import networkx as nx
import copy
try:
    from wfg.wfg_manage import *
    from wfg.wfg_basic_block import *
    from wfg.ast_feature import *
except:
    from wfg_manage import *
    from wfg_basic_block import *
    from ast_feature import *

def add_access_control_node(target_wfg: nx.MultiDiGraph, anchor_points: list):
    if_id = len(target_wfg.nodes)
    target_wfg = add_new_node(target_wfg, if_id, "NODETYPE.IF")
    target_wfg = add_new_node(target_wfg, if_id+1, "NODETYPE.REVERT")
    target_wfg = add_new_node(target_wfg, if_id+2, "NODETYPE.ENDIF")
    target_wfg.add_edge(if_id, if_id + 1)
    target_wfg.add_edge(if_id, if_id + 2)
    successors_copy_anchors = []
    for anchor_point in anchor_points:
        successors_copy = list(target_wfg.successors(anchor_point))
        target_wfg.add_edge(anchor_point, if_id)
        if len(successors_copy_anchors) == 0:
            successors_copy_anchors.extend(successors_copy)
        else:
            if successors_copy != successors_copy_anchors:
                raise RuntimeError("error")
        for successor_copy_anchor in successors_copy_anchors:
            target_wfg.remove_edge(anchor_point, successor_copy_anchor)
            
    for successor_copy_anchor in successors_copy_anchors:
        target_wfg.add_edge(if_id + 2, successor_copy_anchor)
        
    return reset_wfg_block_id(target_wfg)

def add_new_node(target_wfg: nx.MultiDiGraph, new_id: int, nodetype: str):
    target_wfg.add_node(new_id)
    ast_feature = [0] * all_kinds_length
    index = line_feature_index(nodetype)
    if index != -1:
        ast_feature[index] += 1
    target_wfg.nodes[new_id]["blk_vector"] = copy.deepcopy(ast_feature)
    target_wfg.nodes[new_id]["blines"] = []
    target_wfg.nodes[new_id]["weight"] = 1
    return target_wfg

def find_addnode_candidate(targe_graph, cmp_graph, mapping, cost_matrix, target_length):
    node_difference = mapping[0][target_length:]
    has_found_candidate = False
    had_found_indeed = False
    difference_node_if = None
    last_node_id = target_length - 1
    anchor_points = []
    if len(node_difference) == 0:
        return []
    for i in range(len(node_difference)):
        has_found_candidate = False
        for node in cmp_graph.nodes():
            if node_difference[i] == node:
                if len(list(cmp_graph.successors(node))) == 2:
                    difference_node_if = node
                    has_found_candidate = True
                    break
        if has_found_candidate:
            predecessors_nodeif_copy = list(cmp_graph.predecessors(difference_node_if))
            while predecessors_nodeif_copy:
                predecessor = predecessors_nodeif_copy[0]
                predecessors_nodeif_copy = predecessors_nodeif_copy[1:]

                for mapping_index in range(len(mapping[0])):
                    if mapping[0][mapping_index] == predecessor:
                        if mapping_index > last_node_id:
                            predecessors_nodeif_copy.extend(list(cmp_graph.predecessors(predecessor)))
                            continue
                        else:
                            had_found_indeed = True
                            anchor_points.append(mapping_index)
                            break
                
                if had_found_indeed:
                    break

        if had_found_indeed:
            break
                        
    if had_found_indeed:
        return anchor_points
    else:
        return []


def reset_wfg_block_id(target_wfg: nx.MultiDiGraph) -> nx.MultiDiGraph:
    TMP_WFG = nx.MultiDiGraph()
    
    node_id_to_wfg_block = {}
    target_wfg_int = list(target_wfg.nodes)
    for node in target_wfg_int:
        node_id_to_wfg_block[node] = WFGBasicBlock(node)
    nodes_to_be_analyzed = [target_wfg_int[0]]
    start_zero = 0
    edgelist = []
    while nodes_to_be_analyzed:
        # node: int
        node = nodes_to_be_analyzed[0]
        nodes_to_be_analyzed = nodes_to_be_analyzed[1:]
        
        node_block = node_id_to_wfg_block[node]
        
        if not node_block.has_add_temp:
            node_block.block_id = start_zero
            start_zero += 1
            node_block.has_add_temp = True
            TMP_WFG.add_node(node_block)
            TMP_WFG.nodes[node_block].update(target_wfg.nodes[node])
            node_successors_copy = list(target_wfg.successors(node))
            for node_successor in node_successors_copy:
                edgelist.append((node_block, node_id_to_wfg_block[node_successor]))
            nodes_to_be_analyzed.extend(node_successors_copy)
    
    TMP_WFG.add_edges_from(edgelist)
    
    if start_zero != len(target_wfg_int):
        raise RuntimeError(f"transfer target into tmp_wfg error")
    
    return new_wfg_generated(TMP_WFG)


def new_wfg_generated(temp_wfg: nx.MultiDiGraph) -> nx.MultiDiGraph:
    new_target_wfg = nx.MultiDiGraph()
    
    target_wfg_block = list(temp_wfg.nodes)
    nodes_to_be_analyzed = [target_wfg_block[0]]
    edgelist = []
    while nodes_to_be_analyzed:
        # node: wfg_basic_block
        node = nodes_to_be_analyzed[0]
        node_id = node.block_id
        nodes_to_be_analyzed = nodes_to_be_analyzed[1:]
        
        if not node.has_add_new_wfg:
            node.has_add_new_wfg = True
            new_target_wfg.add_node(node_id)
            new_target_wfg.nodes[node_id].update(temp_wfg.nodes[node])
            node_successors_copy = list(temp_wfg.successors(node))
            for node_successor in node_successors_copy:
                edgelist.append((node_id, node_successor.block_id))
            nodes_to_be_analyzed.extend(node_successors_copy)
    
    sorted_edgelist = sorted(edgelist, key=lambda x: x[0])
    new_target_wfg.add_edges_from(sorted_edgelist)
    
    return new_target_wfg