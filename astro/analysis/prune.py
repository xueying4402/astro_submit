from enum import Enum, IntEnum
from slither.core.expressions.identifier import Identifier
from slither.core.expressions.binary_operation import BinaryOperation, BinaryOperationType
from slither.slithir.operations.binary import Binary, BinaryType
from slither.core.cfg.node import NodeType,Node
from slither.slithir.operations.condition import Condition
import networkx as nx
import traceback
import sys
import re
from lib import config

def check_math(function):
    function = str.lower(function)
    function = re.sub(r'^_+|_+$', '', function)
    if function in ["add", "safeadd", "tryadd"]:
        return BinaryType.ADDITION
    if function in ["sub", "safesub", "trysub"]:
        return BinaryType.SUBTRACTION
    if function in ["mul", "safemul", "trymul"]:
        return BinaryType.MULTIPLICATION
    if function in ["div", "safediv", "trydiv"]:
        return BinaryType.DIVISION
    if function in ["mod", "safemod", "trymod"]:
        return BinaryType.MODULO
    return None

def math_replace(call_basic_block, cfg_to_modify, math:BinaryType):
    _, nodetype = list(cfg_to_modify.nodes)[0]._expressions[0]
    if nodetype != NodeType.ENTRYPOINT:
        return False, cfg_to_modify
    parameters = [x for x in call_basic_block._instructions[-1].function.parameters if "int" in str(x.type)]
    try:
        nodescope = list(cfg_to_modify.nodes)[0]._instructions[-1].scope
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
    filescope = list(cfg_to_modify.nodes)[0]._instructions[-1].file_scope
    if len(parameters) != 2:
        return False, cfg_to_modify
    operand1 = parameters[0]
    operand2 = parameters[1]
    return_value = call_basic_block._instructions[-1].lvalue
    operand1_identifier = Identifier(operand1)
    operand2_identifier = Identifier(operand2)
    return_value_identifier = Identifier(return_value)
    new_ir = Binary(return_value, operand1, operand2, math)
    new_ir.set_node(Node(NodeType.RETURN, 0, nodescope, filescope))
    call_basic_block._instructions = call_basic_block._instructions[:-1]
    call_basic_block._instructions.append(new_ir)
    predecessors_copy = list(cfg_to_modify.predecessors(call_basic_block))
    successors_copy = list(cfg_to_modify.successors(call_basic_block))
    if len(successors_copy) == 1:
        if type(successors_copy[0]._instructions[-1]).__name__ in ["LowLevelCall", "HighLevelCall", "InternalCall", "LibraryCall"]:
            return True, cfg_to_modify
        call_basic_block._instructions.extend(successors_copy[0]._instructions)
        call_basic_block._expressions.extend(successors_copy[0]._expressions)
        after_successors_copy = list(cfg_to_modify.successors(successors_copy[0]))
        for node in after_successors_copy:
            cfg_to_modify.add_edge(call_basic_block, node)
        cfg_to_modify.remove_node(successors_copy[0])
    else:
        raise RuntimeError("math_replace error")
    if len(predecessors_copy) == 1:
        cfg_to_modify = merge_predecessor_node(predecessors_copy, call_basic_block, cfg_to_modify)
    return True, cfg_to_modify

def merge_predecessor_node(predecessors_copy, call_basic_block, cfg_to_modify):
    if isinstance(predecessors_copy[0]._instructions[-1], Node) and \
        (predecessors_copy[0]._instructions[-1].type == NodeType.ENTRYPOINT or \
        predecessors_copy[0]._instructions[-1].type == NodeType.ENDIF or \
        predecessors_copy[0]._instructions[-1].type == NodeType.ENDLOOP):
        pass
    elif isinstance(predecessors_copy[0]._instructions[-1], Condition):
        if len(predecessors_copy[0]._expressions):
            (_, node_type) = predecessors_copy[0]._expressions[-1]
            if node_type != NodeType.IF and node_type != NodeType.IFLOOP:
                pass        
        else:
            pass
    else:
        if len(predecessors_copy[0]._expressions):
            (_, node_type) = predecessors_copy[0]._expressions[-1]
        predecessors_copy[0]._instructions.extend(call_basic_block._instructions)
        predecessors_copy[0]._expressions.extend(call_basic_block._expressions)
        predecessors_copy[0]._ir_to_node_map.update(call_basic_block._ir_to_node_map)
        after_successors_copy = list(cfg_to_modify.successors(call_basic_block))
        for node in after_successors_copy:
            cfg_to_modify.add_edge(predecessors_copy[0], node)
        cfg_to_modify.remove_node(call_basic_block)
    return cfg_to_modify
