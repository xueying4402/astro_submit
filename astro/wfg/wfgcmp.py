import math
import os
import sys
import time
import traceback
import shutil
import networkx as nx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from wfg.call_hungarian import call_hungarian
    from wfg.config import *
    from lib.dic_and_file import *
    from wfg.node_manage import *
    from wfg.wfg_manage import *
    from wfg.criterion import *
except:
    from call_hungarian import call_hungarian
    from config import *
    from node_manage import *
    from wfg_manage import *
    from criterion import *

def reasonable_node_cnt(min_cnt, max_cnt, after_add_node=False) -> bool:
    if min_cnt == 0 or max_cnt == 0:
        return False
    # if max_cnt > 3 * min_cnt:
    #     return False
    if max_cnt - min_cnt > 5:
        return False
    
    if after_add_node and max_cnt - min_cnt > 2:
        return False
    
    return True

def cal_nodecost(node1_vec, node2_vec):
    if node1_vec == "dummy_node" or node2_vec == "dummy_node":
        return 1
    if node1_vec == node2_vec:
        return 0
    sim = (node_ecul_sim(node1_vec, node2_vec) + node_cos_sim(node1_vec, node2_vec) ) / 2.0
    val = 1 - sim
    return val

def cal_edgecost(edge1_vec, edge2_vec):
    if edge1_vec is None or edge2_vec is None:
        return 1
    src_cost = cal_nodecost(edge1_vec[0], edge2_vec[0])
    dst_cost = cal_nodecost(edge1_vec[1], edge2_vec[1])
    
    return (src_cost + dst_cost) / 2

def cal_distance(mapping, cost_matrix):
    cost = 0
    for i in range(len(mapping[0])):
        cost += cost_matrix[i][mapping[0][i]]
    return cost

def graph_node_distance(g1, g2, dot_dir, after_add_node):
    MAX_VALUE = 10000
    cost_matrix = []
    g1_indexs = list(g1.nodes())
    g2_indexs = list(g2.nodes())

    matrix_len = max(len(g1), len(g2))
    min_len = min(len(g1), len(g2))
    if min_len == 0:
        return MAX_VALUE, []
    
    for row_id in range(matrix_len):
        row = []
        for column_id in range(matrix_len):
            src = obtain_node_feature(g1, g1_indexs, row_id)
            dst = obtain_node_feature(g2, g2_indexs, column_id)
            cost = cal_nodecost(src, dst)

            if USE_WEIGHT:
                src_weight = obtain_node_weight(g1, g1_indexs, row_id)
                dst_weight = obtain_node_weight(g2, g2_indexs, column_id)
                cost_weight = cost * (src_weight + dst_weight) / 2
                cost = cost_weight
            row.append(cost)
        cost_matrix.append(row)
    if len(cost_matrix) == 0:
        return MAX_VALUE, []
    mapping = call_hungarian(cost_matrix, dot_dir)
    if DEBUG: print("node mapping: ", mapping)
    if DEBUG: print("node matrix: ", cost_matrix)
    try:
        distance = cal_distance(mapping, cost_matrix)
    except Exception as e:
        result = traceback.format_exc()
        raise RuntimeError("Error: {} \n mapping: {} \n mapping length: {} \n {} \n".format(dot_dir , mapping, len(mapping),cost_matrix))
    if after_add_node:
        return distance, []
    addnode_candidate_result =  find_addnode_candidate(g1, g2, mapping, cost_matrix, min_len)
    return distance, addnode_candidate_result

def graph_edge_distance(g1, g2, dot_dir):
    MAX_VALUE = 100
    cost_matrix = []
    g1_indexs = list(g1.edges())
    g2_indexs = list(g2.edges())

    matrix_len = max(len(g1), len(g2))
    min_len = min(len(g1), len(g2))
    if min_len == 0:
        return 0
    diff = min_len * 1.0 / matrix_len
    if diff < 0.5:
        return MAX_VALUE
    for row_id in range(matrix_len):
        row = []
        for column_id in range(matrix_len):
            src = obtain_edge_feature(g1, g1_indexs, row_id)
            dst = obtain_edge_feature(g2, g2_indexs, column_id)
            cost = cal_edgecost(src, dst)
            if USE_WEIGHT:
                src_weight = obtain_edge_weight(g1, g1_indexs, row_id)
                dst_weight = obtain_edge_weight(g2, g2_indexs, column_id)
                cost_weight = cost * (src_weight + dst_weight) / 2
                cost = cost_weight
            row.append(cost)
        cost_matrix.append(row)
    if len(cost_matrix) == 0:
        return -1
    mapping = call_hungarian(cost_matrix, dot_dir)
    if DEBUG: print("edge mapping: ", mapping)
    if DEBUG: print("edge matrix: ", cost_matrix)
    distance = cal_distance(mapping, cost_matrix)
    return distance

def obtain_zero_cnt(g):
	g_indexes = list(g.nodes()) 
	zero_node_cnt = 0
	for index in g_indexes:
		node_v = g.nodes[index]['blines']
		if len(node_v) == 0: zero_node_cnt+=1
	return zero_node_cnt

def weighted_similarity(g_node1, g_node2, node_dis, edge_dis, zero_cnt1, zero_cnt2):
    feature_dis = (node_dis + math.sqrt(edge_dis)) / (g_node1 + g_node2)
    size_dis = abs(float(g_node1 - g_node2)) / (g_node1 + g_node2)
    zero_dis = abs(float(zero_cnt1 - zero_cnt2))/(g_node1 + g_node2)
    
    alpha = 1.15
    beta = 0.05
    gamma = 0.05 
    dis = feature_dis*alpha + size_dis*beta + zero_dis*gamma
    sim = 1 - dis
    return sim if sim > 0 else 0

def compare_wfg(subcfg1, subcfg2, dot_dir, isdeplicate, after_add_node=False) -> int:
    cfg_node_cnt1 = len(subcfg1.nodes())
    cfg_node_cnt2 = len(subcfg2.nodes())

    if not reasonable_node_cnt(min([cfg_node_cnt1, cfg_node_cnt2]), max(cfg_node_cnt1, cfg_node_cnt2), after_add_node):
        return 0, []
    
    if isdeplicate:
        after_add_node = True
    node_dis, addnode_candidate = graph_node_distance(subcfg1, subcfg2, dot_dir, after_add_node)
    if addnode_candidate == None:
        return 0, addnode_candidate
    edge_dis = graph_edge_distance(subcfg1, subcfg2, dot_dir)
    zero_cnt1 = obtain_zero_cnt(subcfg1)
    zero_cnt2 = obtain_zero_cnt(subcfg2)
    sim = weighted_similarity(cfg_node_cnt1, cfg_node_cnt2, node_dis, edge_dis, zero_cnt1, zero_cnt2)
    return round(sim, 3), addnode_candidate

def main(target_wfg_path, compare_wfg_path, isdeplicate=False):
    wfg1 = load_wfg(target_wfg_path)
    wfg2 = load_wfg(compare_wfg_path)
    if wfg1 == None or wfg2 == None:
        raise RuntimeError(f"WFG is none: wfg1: {target_wfg_path}  isnone: {wfg1}  , wfg2: {compare_wfg_path} isnone: {wfg2}")
    
    if isdeplicate:
        if len(wfg1.nodes()) != len(wfg2.nodes()):
            return 0
        
    dot_dir = os.path.dirname(compare_wfg_path)
    address_filename = os.path.basename(os.path.dirname(target_wfg_path))
    dot_dir = os.path.join(dot_dir, address_filename)
    curpid = os.getpid()
    dot_dir = dot_dir + str(curpid)
    if not os.path.exists(dot_dir):
        os.makedirs(dot_dir)

    sim, addnode_candidate = compare_wfg(wfg1, wfg2, dot_dir, isdeplicate)
    if isdeplicate:
        shutil.rmtree(dot_dir)
        return sim
    
    sim_add = 0
    if len(addnode_candidate) != 0:
        wfg1 = add_access_control_node(wfg1, addnode_candidate)
        sim_add, _ = compare_wfg(wfg1, wfg2, dot_dir, isdeplicate, after_add_node=True)
        
    shutil.rmtree(dot_dir)
    if (sim > 0.8) or (sim_add > 0.8):
        if sim >= sim_add:
            result_list = [False, target_wfg_path, compare_wfg_path, sim, sim_add]
        else:
            result_list = [True, target_wfg_path, compare_wfg_path, sim_add, sim]
        return result_list
    else:
        return "Not Sim"

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Please provide two command-line arguments.")
    else:
        filepath1 = sys.argv[1]
        filepath2 = sys.argv[2]
        result = main(filepath1, filepath2)
        print(result)


