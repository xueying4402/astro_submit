import slither
import shutil
import os
import sys
import pydot
import glob
import traceback
import networkx as nx
from collections import defaultdict
import matplotlib.pyplot as plt
from varnode import *
from collections import defaultdict
from slither.core.declarations.solidity_variables import SolidityFunction
from slither.core.declarations.function import Function
from slither.core.variables.variable import Variable
from slither.printers.call.call_graph import *
from slither.slithir.operations.assignment import Assignment
from slither.slithir.operations.init_array import InitArray
from slither.slithir.variables.constant import Constant
from slither.slithir.variables.temporary import TemporaryVariable
from slither.core.cfg.node import NodeType
from cfg import *
from basic_block import *
import copy
from util import *
import slither_globals
from lib import config
from lib.extra_node import ExtraNodeType
from prune import *


class ICFG:
    """
        Builds an inter procedural cfg
    """
    icfg_generated = {}
    locals_to_declare = {}
    icfg_objects = {}
    function_to_graph = []
    uid = 1
    
    def __init__(self, slither_obj, contract, function, callgraph, graph_dir, dump_graph, log):
        self._slither = slither_obj
        self._root_nodes = []
        self._leaf_nodes = []
        self._all_predecessors = {}
        self._all_successors = {}
        self._callgraph = callgraph
        self._contract = contract
        self._function = function
        self._dump_graph = dump_graph
        self._log = log
        self.blockid = {}
        self._function_icfg = None
        self._result_dir = graph_dir
        self._visit_stack = []
        self._recursion_present = False
        self.setup()
    
    def get_index(self, graph):
        index = 0
        blockid = {}
        
        for node in graph.nodes:
            blockid[node] = index
            index = index + 1
        
        return blockid
        
    def setup(self):
        call_context = []
        self._function_icfg = self.build_icfg(self._contract, self._function, call_context, self._result_dir)
        self.visit_nodes()
        compute_ancesters_decendents(self._function_icfg, self._leaf_nodes, self._root_nodes, self._all_predecessors, self._all_successors)
        convert_set_to_list(self._all_predecessors)
        convert_set_to_list(self._all_successors)
        ICFG.icfg_objects[self._function] = self
        
        if self._recursion_present == True:
            self.add_backedge_for_recusive_call()

        if self._dump_graph == True:
            self.print_icfg_dot(self._result_dir, self._function, self._function_icfg)




    @staticmethod
    def initialize_icfg(contracts):
        for contract in contracts:
            ICFG.icfg_generated[contract] = {}
            
            for function in contract.functions:
                ICFG.icfg_generated[contract][function] = None
            
            for modifier in contract.modifiers:
                ICFG.icfg_generated[contract][modifier] = None


    def add_backedge_for_recusive_call(self):
        recursive_call = None
        from_to = {}
        
        for node in self._function_icfg.nodes:
            if node._is_recursive_call != None:
                recursive_call = node._is_recursive_call
                node._is_recursive_call = None
                
                if from_to.get(str(node._label)) == None:
                    from_to[str(node._label)] = []
                
                from_to[str(node._label)].insert(0, node)
            
            elif node._label != None:
                if from_to.get(str(node._label)) == None:
                    from_to[str(node._label)] = []
                from_to[str(node._label)].insert(1, node)
        
        if recursive_call != None:
            for key in from_to.keys():
                from_node = from_to[key][0]
                to_node = from_to[key][1]
                last_instruction = from_node._instructions[-1]
                from_node._instructions = from_node._instructions[:-1]

                if len(last_instruction.function.parameters) != 0:
                    copy_basic_block = self.interprocedural_call_copy_block(last_instruction, recursive_call)
                    from_node._instructions = from_node._instructions + copy_basic_block._instructions
                    from_node._ir_to_node_map.update(copy_basic_block._ir_to_node_map)
                
                if self._function_icfg.in_degree(to_node) == 0:
                    new_bb = copy.deepcopy(to_node)
                    self._function_icfg.add_edge(new_bb, to_node)
                
                self._function_icfg.add_edge(from_node, to_node)

    # This function visits the nodes of ICFG and collects information
    # such as root node, leaf nodes, undeclared locals etc.
    def visit_nodes(self):
        lvalue_locals = []
        rvalue_locals = []
        
        for node in self._function_icfg.nodes:
            if self._function_icfg.in_degree(node)== 0:
                self._root_nodes.append(node)
            
            if self._function_icfg.out_degree(node)== 0:
                self._leaf_nodes.append(node)
            
            for instr in node._instructions:
                if hasattr(instr, 'lvalue'):
                    lvalue = instr.lvalue
                    if type(lvalue).__name__ == 'LocalVariableSolc' or type(lvalue).__name__ == 'LocalVariable':
                        lvalue_locals.append(lvalue)
                
                if hasattr(instr, 'rvalue'):
                    rvalue = instr.rvalue
                    if type(rvalue).__name__ == 'LocalVariableSolc' or type(rvalue).__name__ == 'LocalVariable':
                        rvalue_locals.append(rvalue)
                
                if not hasattr(instr, 'rvalue') and not type(instr).__name__ == 'Node':
                    vars_used = instr.used

                    for var_used in vars_used:
                        if hasattr(instr, 'lvalue'):
                            if var_used == instr.lvalue:
                                continue
                            
                            elif type(var_used).__name__ == 'LocalVariableSolc' or type(var_used).__name__ == 'LocalVariable':
                                rvalue_locals.append(var_used)
                        else:
                            if type(var_used).__name__ == 'LocalVariableSolc' or type(var_used).__name__ == 'LocalVariable':
                                rvalue_locals.append(var_used)

        ICFG.locals_to_declare[self._function] = list(set(rvalue_locals))

    # This function inline the caller cfg with teh caller cfg at the place of the interprocedural call
    def inline_cfg(self, icfg, cfg_to_modify, call_basic_block, copy_basic_block, return_basic_block, function_ref, compose='N'):
        # get the predecessors and successors of the call_basic_block
        predecessors_copy = list(cfg_to_modify.predecessors(call_basic_block))
        successors_copy = list(cfg_to_modify.successors(call_basic_block))

        # We first compose the caller cfg with callee cfg together and remove the call basic block
        # from the composed graph. We modify the basic block by removing the call instruction and 
        # append the copy basic block instructions, now we add basic block again in the composed graph
        # and add edges from the call basic block to the root nodes of the callee cfg.
        # Add edges from the callee cfg leaf nodes to the previous successors of call basic block
        # In this way we inline the calle cfg with caller cfg
        if compose == 'N':
            # Compose caller cfg with callee icfg
            cfg_to_modify = nx.compose(cfg_to_modify, icfg)
            cfg_to_modify.remove_node(call_basic_block) # Remove the call basic block
            call_instr =  call_basic_block._instructions[-1]
            call_basic_block._instructions = call_basic_block._instructions[:-1] # Remove the call instruction from the basic block

            # Add the copy basic block instruction to the call basic block
            if len(copy_basic_block._instructions) != 0:
                call_basic_block._instructions.extend(copy_basic_block._instructions)
                call_basic_block._ir_to_node_map.update(copy_basic_block._ir_to_node_map)
                call_basic_block._expressions.extend(copy_basic_block._expressions)
            
            # Get the root nodes and the leaf nodes of the call basic block
            leaf_nodes = self.get_leaf_basic_blocks(icfg)
            root_node = self.get_root_basic_block(icfg)
            function_name = function_ref.contract.name + "." + function_ref.name

            func_enter = 'Enter: ' + function_ref.name
            func_exit = 'Exit: ' + function_ref.name

            # If the call basic block is not empty, then add it again in the composed graph, and
            # add edges from the call basic block to the root node of the icfg
            if len(call_basic_block._instructions) != 0:
                add_edge_from_nodes(cfg_to_modify, predecessors_copy, call_basic_block)
                cfg_to_modify.add_edge(call_basic_block, root_node, key=func_enter, ref=function_name)
            
            # Else add edges from the predecessors of the call basic block to the root node of icfg
            else:
                root_node._is_True = call_basic_block._is_True
                add_edge_from_nodes(cfg_to_modify, predecessors_copy, root_node, func_enter, function_name)
            #cfg_to_modify = nx.contracted_edge(cfg_to_modify, (basic_block, root_node), self_loops=False)

            # : remove the call instruction all together
            if return_basic_block is not None:
                new_basic_block = return_basic_block
                new_basic_block._ir_to_node_map[call_instr] = call_basic_block._ir_to_node_map[call_instr]
            
            else:
                new_basic_block = None
                
                #BasicBlock([call_instr])
            
            if len(leaf_nodes) == 0:
                leaf_nodes = [root_node]
            
            if new_basic_block is not None:
                # Add edges from the leaf nodes to the return basic block
                for node in leaf_nodes:
                    #for successor in successors_copy:
                    cfg_to_modify.add_edge(node, new_basic_block, key=func_exit, ref=function_name)
                
                # Finally add edges from the new basic block to the successors of the call basic block
                for successor in successors_copy:
                    cfg_to_modify.add_edge(new_basic_block, successor)
            else:
                for successor in successors_copy:
                    for node in leaf_nodes:
                        cfg_to_modify.add_edge(node, successor, key=func_exit, ref=function_name)

        else:
            pass
        
        return cfg_to_modify

    def inline_cfg_prune(self, icfg, cfg_to_modify, call_basic_block, copy_basic_block, return_basic_block, function_ref, compose='N'):
        if len(icfg.nodes) == 1:
            _, nodetype = list(icfg.nodes)[0]._expressions[0]
            if nodetype == NodeType.ENTRYPOINT:
                return cfg_to_modify
            raise RuntimeError("not ENTRY_POINT")
        
        predecessors_copy = list(cfg_to_modify.predecessors(call_basic_block))
        successors_copy = list(cfg_to_modify.successors(call_basic_block))
        
        if type(function_ref).__name__ == "Modifier":
            if len(function_ref.state_variables_written) == 0 and len([n for n in function_ref.nodes if n.is_conditional(False)]) == 0:
                self._log.info(f"skip modifier: {function_ref.name}")
                cfg_to_modify.remove_node(call_basic_block)
                if len(successors_copy) in [0, 1]:
                    if type(successors_copy[0]._instructions[-1]).__name__ in ["LowLevelCall", "HighLevelCall", "InternalCall", "LibraryCall"]:
                            for predecessor in predecessors_copy:
                                cfg_to_modify.add_edge(predecessor, successors_copy[0])
                    elif len(predecessors_copy) == 1:
                        for predecessor in predecessors_copy:
                            cfg_to_modify.add_edge(predecessor, successors_copy[0])
                        cfg_to_modify = merge_predecessor_node(predecessors_copy, successors_copy, cfg_to_modify)
                    else:
                        for predecessor in predecessors_copy:
                                cfg_to_modify.add_edge(predecessor, successors_copy[0])
                else:
                    raise RuntimeError("modifier error")
                return cfg_to_modify

        # We first compose the caller cfg with callee cfg together and remove the call basic block
        # from the composed graph. We modify the basic block by removing the call instruction and 
        # append the copy basic block instructions, now we add basic block again in the composed graph
        # and add edges from the call basic block to the root nodes of the callee cfg.
        # Add edges from the callee cfg leaf nodes to the previous successors of call basic block
        # In this way we inline the calle cfg with caller cfg
        if compose == 'N':
            # Compose caller cfg with callee icfg
            cfg_to_modify = nx.compose(cfg_to_modify, icfg)
            call_instr =  call_basic_block._instructions[-1]
            call_basic_block._instructions = call_basic_block._instructions[:-1] # Remove the call instruction from the basic 
            call_basic_block._expressions = call_basic_block._expressions[:-1] #Remove the call expressions from the basic

            # Get the root nodes and the leaf nodes of the call basic block
            leaf_nodes = self.get_leaf_basic_blocks(icfg)
            root_node = self.get_root_basic_block(icfg, icfg=cfg_to_modify, de_entrypoint=True)
            function_name = function_ref.contract.name + "." + function_ref.name

            func_enter = 'Enter: ' + function_ref.name
            func_exit = 'Exit: ' + function_ref.name

            # If the call basic block is not empty, then add it again in the composed graph, and
            # add edges from the call basic block to the root node of the icfg
            diff = 0
            if len(root_node) == 1:
                root_node = root_node[0]
                # if len(call_basic_block._instructions) != 0:
                call_basic_block._instructions.extend(root_node._instructions)
                call_basic_block._ir_to_node_map.update(root_node._ir_to_node_map)
                call_basic_block._expressions.extend(root_node._expressions)
                # add_edge_from_nodes(cfg_to_modify, predecessors_copy, call_basic_block, de_entrypoint=True, icfg=icfg)
                rootnode_successors_copy = list(cfg_to_modify.successors(root_node))
                for node in rootnode_successors_copy:
                    cfg_to_modify.add_edge(call_basic_block, node, key="successor_5")
                cfg_to_modify.remove_node(root_node)
            elif len(root_node) == 0:
                raise RuntimeError("len(root_node) == 0")
                pass
            else:
                raise RuntimeError("the root_node of callee function != 1", function_ref.name)
            



            # : remove the call instruction all together
            if return_basic_block is not None:
                new_basic_block = return_basic_block
                new_basic_block._ir_to_node_map[call_instr] = call_basic_block._ir_to_node_map[call_instr]
            
            else:
                new_basic_block = None
                
            
            if len(leaf_nodes) == 0:
                leaf_nodes = [root_node]

            for node in successors_copy:
                cfg_to_modify.remove_edge(call_basic_block, node)
                
            if len(leaf_nodes) > 1 or len(successors_copy) > 1:
                for successor in successors_copy:
                    for node in leaf_nodes:
                        cfg_to_modify.add_edge(node, successor, key="successor_5", ref=function_name)
            elif len(leaf_nodes) == 1 and (leaf_nodes[0] == root_node):
                if len(successors_copy) == 0:
                    pass
                elif len(successors_copy) == 1:
                    if type(successors_copy[0]._instructions[-1]).__name__ in ["LowLevelCall", "HighLevelCall", "InternalCall", "LibraryCall"]:
                        for successor in successors_copy:
                            cfg_to_modify.add_edge(call_basic_block, successor, key="successor_4",  ref=function_name)
                        pass
                    else:
                        call_basic_block._instructions.extend(successors_copy[0]._instructions)
                        call_basic_block._ir_to_node_map.update(successors_copy[0]._ir_to_node_map)
                        call_basic_block._expressions.extend(successors_copy[0]._expressions)
                        after_successors_copy = list(cfg_to_modify.successors(successors_copy[0]))
                        for node in after_successors_copy:
                            cfg_to_modify.add_edge(call_basic_block, node, key="successor_3")
                        cfg_to_modify.remove_node(successors_copy[0])
                else:
                    raise RuntimeError("successors numbers is not equal to 1" + str(call_basic_block) + "real node: " + str(len(successors_copy)))
            else:
                if len(successors_copy) == 0:
                    pass
                elif len(successors_copy) == 1:
                    if type(successors_copy[0]._instructions[-1]).__name__ in ["LowLevelCall", "HighLevelCall", "InternalCall", "LibraryCall"] or \
                        (isinstance(leaf_nodes[0]._instructions[-1], Node) and \
                            (leaf_nodes[0]._instructions[-1].type == NodeType.ENDIF or \
                            leaf_nodes[0]._instructions[-1].type == NodeType.ENDLOOP)):
                        for successor in successors_copy:
                            for node in leaf_nodes:
                                
                                cfg_to_modify.add_edge(node, successor, key=func_exit, ref=function_name)
                    else:
                        leaf_nodes[0]._instructions.extend(successors_copy[0]._instructions)
                        leaf_nodes[0]._ir_to_node_map.update(successors_copy[0]._ir_to_node_map)
                        leaf_nodes[0]._expressions.extend(successors_copy[0]._expressions)
                        after_successors_copy = list(cfg_to_modify.successors(successors_copy[0]))
                        for node in after_successors_copy:
                            cfg_to_modify.add_edge(leaf_nodes[0], node, key="successor_2")
                        cfg_to_modify.remove_node(successors_copy[0])
                else:
                    raise RuntimeError("Something error")

                
            
            if len(predecessors_copy) == 1:
                cfg_to_modify = merge_predecessor_node(predecessors_copy, call_basic_block, cfg_to_modify)

        else:
            pass
        
        return cfg_to_modify

    def get_function_ref(self, graph):
        nodes = [x for x in graph.nodes]
        return nodes[0]._instructions[0].function
    
    def reset_icfg(self, graph):
        pass
    
    def get_root_basic_block(self, graph, icfg=None, de_entrypoint=False):
        if de_entrypoint:
            root_node = []
            entry_node = BasicBlock([])
            for node, adjacency in graph.adjacency():
                instr_type = node._instructions[0]
                if type(instr_type).__name__ == 'Node' and instr_type.type == NodeType.ENTRYPOINT:
                    if len(node._instructions) > 1:
                        raise RuntimeError("ENTRYPOINT ERROR: ", str(node))
                    for key in adjacency:
                        root_node.append(key)
                    icfg.remove_node(node)
                    return root_node
        root_node = None
        nodes = [x for x in graph.nodes if graph.in_degree(x) == 0]
        
        for node in nodes:
            instr_type = node._instructions[0]
            if type(instr_type).__name__ == 'Node' and instr_type.type == NodeType.ENTRYPOINT:
                root_node = node
        return root_node

    def get_leaf_basic_blocks(self, graph):
        leaf_nodes = [x for x in graph.nodes if graph.out_degree(x)== 0 and graph.in_degree(x) >= 1]
        new_leaf_nodes = []
        for node in leaf_nodes:
            if len(node._instructions) > 0 and isinstance(node._instructions[-1], SolidityCall) and node._instructions[-1].function.name == "revert()":
                continue
            new_leaf_nodes.append(node)
        return new_leaf_nodes

    # This function traverses the basic blocks in the cfg, and for every 
    # interprocedural call it inlines the callee with the caller.
    def traverse_cfg(self, cfg_obj, call_context, result_dir):
        cfg = cfg_obj._cfg
        caller_cfg = copy.deepcopy(cfg)
        
        call_basic_blocks = [cfg_obj._ircall_to_bb[ir_call]._prev_bb for ir_call in cfg_obj._ircall_to_bb.keys() \
                             if cfg_obj._ircall_to_bb[ir_call]._prev_bb is not None]

        for basic_block in call_basic_blocks:
            last_instruction = basic_block._instructions[-1]

            # Low level calls are external calls, we do not need to inline them as the callee function can be anyone
            if type(last_instruction).__name__ == 'LowLevelCall':
                pass
            
            elif type(last_instruction).__name__ == 'HighLevelCall' or type(last_instruction).__name__ == 'InternalCall' or type(last_instruction).__name__ == 'LibraryCall':
                is_tainted = False

                # For high level calls, callee can still belong to an external contract, hence we should check whether the callee 
                # belongs to any external contract or whether the call destination is tainted. If any of the above cases are true, we 
                # do not inline the callee, otherwise we inline the callee with the caller
                if type(last_instruction).__name__ == 'HighLevelCall':
                    node = basic_block._ir_to_node_map[last_instruction]
                    is_tainted = is_tainted_destination(last_instruction.destination, node)
                
                # If the call destination is tainted we do not do anything
                if is_tainted:
                    continue

                function = last_instruction.function
                contract = function.contract
                

                if type(function).__name__ == 'FunctionSolc' or type(function).__name__ == "FunctionContract" \
                    or (config.get_normalize() and type(function).__name__ == "Modifier"):
                    if contract not in self._slither.contracts:
                        continue
                    
                    # Else we inline the callee with the caller
                    else:
                        math = check_math(function.name)
                        if config.get_prune() and math:
                            real_math,  caller_cfg = math_replace(basic_block, caller_cfg, math)
                            if real_math:
                                continue
                            else:
                                pass
                        # Get the icfg for the caller
                        copy_call_context = copy.copy(call_context)
                        if cfg_obj._function not in copy_call_context:
                            copy_call_context.append(cfg_obj._function)
                        
                        partial_icfg = self.build_icfg(contract, function, copy_call_context, result_dir)

                        if type(partial_icfg).__name__ == 'FunctionSolc' or type(partial_icfg).__name__ == "FunctionContract":
                            basic_block._is_recursive_call = function
                            basic_block._label = ICFG.uid
                            self._recursion_present = True
                        
                        else:
                            # Get the list of nodes from the callee icfg
                            nodes = list(partial_icfg.nodes) #[node for node in partial_icfg.nodes]
                            
                            # If the number of nodes is not zero
                            if len(nodes) != 0:
                                try:
                                    # Creates the copy block for interprocedural call, this maps the formal parameters 
                                    # with the actual parameters by creating an assignment IR.
                                    copy_basic_block = self.interprocedural_call_copy_block(last_instruction, function)
                                    
                                    callee_cfg = callee_cfg_copy(partial_icfg, basic_block._block_id)

                                    if len(ICFG.function_to_graph) != 0:
                                        if function == ICFG.function_to_graph[-1]:
                                            ICFG.function_to_graph.remove(function)
                                            root_node = [x for x in callee_cfg.nodes if callee_cfg.in_degree(x) == 0]
                                            root_node[0]._label = ICFG.uid
                                    
                                    self.add_calling_context(copy_call_context, function, callee_cfg)
                                    return_basic_block = self.interprocedural_call_return_block(last_instruction, callee_cfg, function)

                                    # Inline the callee icfg with the caller icfg 
                                    if config.get_normalize():
                                        caller_cfg = self.inline_cfg_prune(callee_cfg, caller_cfg, basic_block, copy_basic_block, return_basic_block, function)
                                    else:
                                        caller_cfg = self.inline_cfg(callee_cfg, caller_cfg, basic_block, copy_basic_block, return_basic_block, function)
                                
                                except:
                                    traceback.print_exc()
                                    sys.exit(1)
                            
                            else:
                                pass
                        
                        if len(ICFG.function_to_graph) != 0:
                            if cfg_obj._function == ICFG.function_to_graph[-1]:
                                ICFG.function_to_graph.remove(cfg_obj._function)
                                root_node = [x for x in caller_cfg.nodes if caller_cfg.in_degree(x) == 0]
                                root_node[0]._label = ICFG.uid
            else:
                pass
        
        return caller_cfg

    def add_calling_context(self, call_context, function, callee_cfg):
        for node in callee_cfg.nodes:
            prev_call_context = node._call_context
            try:
                index = prev_call_context.index(function)
            except ValueError as e:
                index = -1
            
            if index == -1:
                node._call_context = call_context
            
            else:
                prev_call_context = prev_call_context[index:]
                node._call_context = call_context + prev_call_context

    # This function creates an assignment IR for every formal parameter. The lvalue 
    # of the IR is the actual parameter and rvalue or the IR is the corresponding
    # formal parameter. Put all these assignment instruction in a separate basic block
    def interprocedural_call_copy_block(self, call_instruction, callee_function):
        formal_parameters = call_instruction.arguments
        actual_parameters = callee_function.parameters
        basic_block = BasicBlock([])
        basic_block._expressions.extend([("CALLSITE", [])])

        try:
            for i in range(0, len(formal_parameters)):
                var_right = formal_parameters[i]
                var_left = actual_parameters[i]

                if str(var_left) == '':
                    continue
                if isinstance(var_right, list):
                    ir = InitArray(var_right, var_left)
                
                else:
                    ir = Assignment(var_left, var_right, var_right.type)
                basic_block._instructions.append(ir)
                basic_block._ir_to_node_map[ir] = call_instruction.node
            
            return basic_block
        
        except:
            traceback.print_exc()
            sys.exit(1)


    # This function creates a separate basic block for return values.
    # That basic block contains the assignment IR where the lvalue is the lvalue of
    # the actual call instruction and the rvalue is the returned value from the caller.
    # Now the caller can have multiple returns. So, we create a temporary variable, which 
    # holds the different return values, and this temporary variable is then assigned to lvalue
    # of the call instruction
    def interprocedural_call_return_block(self, call_instruction, partial_icfg, function):
        cfg_obj = CFG.function_cfg[function]
        leaf_basic_blocks = self.get_leaf_basic_blocks(partial_icfg)
        is_return_block = False
        
        # It checks whether there exist an explit return statement 
        # in this function, because if it does then cfg_obj._return_to_phi
        # already mapped that return IR into an corresponding assignment IR 
        # during the cfg generation, where temp var is serving as a phi var to 
        # capture different return values for different return IRs
        if len(cfg_obj._return_to_phi.keys()) != 0:
            for leaf_basic_block in leaf_basic_blocks:
                last_instruction = leaf_basic_block._instructions[-1]
                
                # Updates the basic block by removing the return IR and instead replaces 
                # that with assignment IR where lvalue is the phi temporary variable and 
                # rvalue is the returned value
                if type(last_instruction).__name__ == 'Return':
                    leaf_basic_block._instructions = leaf_basic_block._instructions[:-1]
                    leaf_basic_block._expressions = leaf_basic_block._expressions[:-1]
                    leaf_basic_block._instructions.append(cfg_obj._return_to_phi[last_instruction])
                    is_return_block = True
        
        # Now in solidity a function can define the returned variable during function declaration without
        # even using an return statement in it's body. So, during our cfg generation process we detect
        # such kind of return values and create a list as cfg_obj._new_phi_return, so if the list is not 
        # empty it means such kind of return value exist and we should process them by puting into a 
        # basic block to simuate the return and add edges from the leaf nodes to the basic block
        if len(cfg_obj._new_phi_return) != 0:
            is_return_block = True
            basic_block = BasicBlock(cfg_obj._new_phi_return)
            add_edge_from_nodes(partial_icfg, leaf_basic_blocks, basic_block)
            partial_icfg = merge_predecessor_node(list(partial_icfg.predecessors(basic_block)), basic_block, partial_icfg)
        
        # If the function has return values, then create a return basic block with an assignment
        # IR, where the lvalue is the lvalue of the actual call instruction and rvalue is the phi
        # variable
        if is_return_block:
            if call_instruction.lvalue != None:
                return_basic_block = BasicBlock([])
                ir = Assignment(call_instruction.lvalue, cfg_obj._phi_return_variable, cfg_obj._phi_return_variable.type)
                return_basic_block._instructions.append(ir)
                return_basic_block._expressions.extend([("RETURNSITE", [])])
            
            else:
                return_basic_block = None
        
        # Set the return basic block to be None
        else:
            return_basic_block = None

        if return_basic_block == None and hasattr(call_instruction, 'lvalue') and call_instruction.lvalue is not None:
            lvalue = call_instruction.lvalue

            if type(lvalue.type).__name__ == 'ElementaryType':
                r_value = Constant("1")
                return_basic_block = BasicBlock([])
                ir = Assignment(call_instruction.lvalue, r_value, call_instruction.lvalue.type)
                return_basic_block._instructions.append(ir)

        return return_basic_block

    # Builds ICFG for the function in the 
    def build_icfg(self, contract, function, call_context, result_dir):
        # If the icfg for the function already exists, return that
        # Else, generates the ICFG by building it's CFG first and 
        # converts any interprocedural calls by inline the callee function
        # within the caller

        if function not in self._visit_stack:
            self._visit_stack.append(function)

        else:
            ICFG.function_to_graph.append(function)
            ICFG.uid = ICFG.uid + 1
            return function
        
        if ICFG.icfg_generated[contract][function] is None:
            # Generates the CFG if not exist
            if function not in CFG.function_cfg.keys():
                cfg_obj = CFG(self._slither, contract, function, result_dir, self._dump_graph, self._log, ICFG.icfg_objects)
                CFG.function_cfg[function] = cfg_obj
            else:
                cfg_obj = CFG.function_cfg[function]
            
            # Generates the icfg by travesring the CFG and looking for any
            # interprocedural calls and inline them to generate a full icfg
            icfg = self.traverse_cfg(cfg_obj, call_context, result_dir)
            ICFG.icfg_generated[contract][function] = icfg

        self._visit_stack.remove(function)
        return ICFG.icfg_generated[contract][function]
    
    def reset_revert_nodetype(self, icfg, node):
        predecessors_copy = list(icfg.successors(node))
        for precessor in predecessors_copy:
            if len(precessor._instructions) and type(precessor._instructions[-1]).__name__ == "SolidityCall" and \
                precessor._instructions[-1].function.name == "revert()":
                    if len(precessor._expressions):
                        precessor._expressions = precessor._expressions[:-1]
                        precessor._expressions.append(["revert()()", ExtraNodeType.REVERT])

    def reset_block_id(self, icfg):
        icfg_nodes = list(icfg.nodes)
        icfg_nodes_length = len(icfg_nodes)
        if icfg_nodes_length == 0:
            return icfg
        nodes_to_be_analyzed = [icfg_nodes[0]]
        nodes_has_analyzed = []
        _, nodetype = nodes_to_be_analyzed[0]._expressions[0]
        if nodetype != NodeType.ENTRYPOINT:
            if self._function.name not in ["slitherConstructorVariables", "slitherConstructorConstantVariables"]:
                print(f"reset block_id Error: {self._function.name}")
            return icfg
        start_zero = 0
        for icfg_node in icfg_nodes:
            icfg_node._has_reset = False
        while nodes_to_be_analyzed:
            node = nodes_to_be_analyzed[0]
            nodes_has_analyzed.append(node)
            nodes_to_be_analyzed = nodes_to_be_analyzed[1:]
            
            if len(node._expressions):
                _, lastnodetype = node._expressions[-1]
                if lastnodetype == NodeType.IF or lastnodetype == NodeType.IFLOOP:
                    self.reset_revert_nodetype(icfg, node)

            if not node._has_reset:
                node._block_id = start_zero
                start_zero += 1
                node._has_reset = True
                nodes_to_be_analyzed.extend(list(icfg.successors(node)))
        if icfg_nodes_length != start_zero:
            self._log.info(f"reset block_id length Error: {config.get_wfg_dir()} {self._function.name}\ttarget last_id: {icfg_nodes_length}\treal last_id: {start_zero}")
            node_to_be_removed = []
            for node in icfg_nodes:
                if node not in nodes_has_analyzed:
                    node_to_be_removed.append(node)
            
            for node in node_to_be_removed:
                icfg.remove_node(node)
            if self._function.name != "distr":
                self._log.info(f"new dead_code in {self._function.name}")

    def print_icfg_dot(self, graph_dir, function, graph, name=None):
        if config.skip_dump_file(function.name):
            return
        if len(list(graph.nodes())) == 0:
            return
        if config.get_dappScan():
            graph_dir = config.get_dapp_graph_dir(graph_dir, function.full_name)
        
        self.reset_block_id(graph)
        content = ''

        dot_file_name = function.full_name + "_icfg.dot"
        dot_file_path = os.path.join(graph_dir, dot_file_name)
        with open(dot_file_path, 'w', encoding='utf8') as fp:
            nx.drawing.nx_pydot.write_dot(graph, fp)


        if config.get_scale():
            return

        (dot_graph, ) = pydot.graph_from_dot_file(dot_file_path)

        for i, node in enumerate(dot_graph.get_nodes()):
            node.set_shape('box')

        for i, edge in enumerate(dot_graph.get_edges()):
            key = edge.get('key')
            if key.startswith('"Enter') or key.startswith('"Exit'):
                edge.set_label(edge.get('key'))

        png_file_name = function.full_name + "_icfg.png"
        png_file_path = os.path.join(graph_dir, png_file_name)
        try:
            dot_graph.write_png(png_file_path)
        except:
            print("icfg print error：", png_file_path)

    '''    
    # Print the CFG in a dot file
    def print_icfg_dot(self, graph_dir, function, graph, name=None):
        blockid = self.get_index(graph)
        content = ''
        if name is not None:
            file_n = function.name + name + "_icfg.dot"
        else:
            file_n = function.name + "_icfg.dot"
        
        filename = os.path.join(graph_dir,file_n)
        
        with open(filename, 'w', encoding='utf8') as f:
            f.write('digraph{\n')
            src_label = ""
            target_label = ""
            
            for edges in graph.edges:
                src_block = edges[0]
                target_block = edges[1]
                src_label = str(blockid[src_block])
                target_label = str(blockid[target_block])
                src_label += str(src_block)
                f.write('{}[label="{}"];\n'.format(blockid[src_block], src_label))
                target_label += str(target_block)
                f.write('{}[label="{}"];\n'.format(blockid[target_block], target_label))
                f.write('{}->{};\n'.format(blockid[src_block], blockid[target_block]))
            f.write("}\n")
    '''

def callee_cfg_copy(partial_icfg, block_id):
    slither_globals.is_Iblock_id = True
    slither_globals.Iblock_id = block_id
    callee_cfg = copy.deepcopy(partial_icfg)
    slither_globals.is_Iblock_id = False
    return callee_cfg