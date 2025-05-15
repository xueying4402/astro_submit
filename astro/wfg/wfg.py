import sys
import time
import os

import networkx as nx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from analysis.main_helper import *
# from aninfer.analysis.main_helper import *
from slither.core.cfg.node import NodeType
from wfg.ast_feature import *
from wfg.wfg_manage import *
from lib import config
from lib.timing_decorator import timing_decorator
from crytic_compile.localize import config as compile_config
import copy
function_visibility = ['public', 'external']

DEBUG = True
USE_WEIGHT = True

@timing_decorator
def code2wfg(slither_obj, icfg_objects, target_contracts, src_file='None', root_line = -1, address = None):
    cfg = get_icfg(slither_obj, icfg_objects, target_contracts, address)

def get_icfg(slither_obj, icfg_objects, target_contracts, address, src_file='None', root_line = -1, ):
	
	ast_feature = []

	reserved_lines = {}
	start_t = time.time()
	if DEBUG: start_t = time.time() 
	if (root_line == -1):
		reserved_lines = {}
	else:
		# Sliced lines need reserved
		reserved_lines = slicing(src_file, root_line)
	if DEBUG: end_t = time.time()
	if DEBUG: print('slicing time, ', end_t - start_t )
	if DEBUG: start_t = time.time()

	cfg=build_ICFG(slither_obj, icfg_objects, target_contracts, ast_feature, reserved_lines, address)

	if DEBUG: end_t = time.time()
	if DEBUG: print('build_CFGs, ', end_t - start_t )
	#print reserved_lines

	# Need to set line_weigth for cfg nodes
	#print 'get_cfg, ', root_line
	if root_line != -1 and USE_WEIGHT:
		set_line_weight(cfg, reserved_lines)
	return cfg

def slicing():
    pass

def set_line_weight():
	pass

def build_ICFG(slither_obj, cfg_data, target_contracts, ast_feature, reserved_lines, address):

	for contract in slither_obj.contracts:
		for function in contract.functions:
			if ((function.visibility not in function_visibility) or \
				function.view or \
				function.pure):
				continue
			if function == None:
				print("???")
				continue
			if config.skip_dump_file(function.name):
				continue
			nx_icfg = cfg_data[contract][function]
			wfg_generated(nx_icfg, function.full_name)



def wfg_generated(nx_icfg, function_name):
	NCFG = nx.MultiDiGraph()
	nodelist = []
	edgelist = []
	nx_icfg_nodes_num = list(nx_icfg.nodes)
	if len(nx_icfg_nodes_num) in [0, 1]:
		return
	nodes_to_be_analyzed = [nx_icfg_nodes_num[0]]
	_, nodetype = nodes_to_be_analyzed[0]._expressions[0]
	if nodetype != NodeType.ENTRYPOINT:
		print(f"generate wfg Error: {function_name}")
		return
	for icfg_node in nx_icfg_nodes_num:
		icfg_node._has_add_wfg = False
	while nodes_to_be_analyzed:
		node = nodes_to_be_analyzed[0]
		nodes_to_be_analyzed = nodes_to_be_analyzed[1:]
  
		if not node._has_add_wfg:
			node._has_add_wfg = True
			node_block_id = node._block_id
			NCFG.add_node(node_block_id)
			ast_feature = [0] * all_kinds_length
			for (expression, nodetype) in node._expressions:
				index = line_feature_index(str(nodetype))
				if index != -1:
					ast_feature[index] += 1
			NCFG.nodes[node_block_id]["blk_vector"] = copy.deepcopy(ast_feature)
			NCFG.nodes[node_block_id]["blines"] = []
			NCFG.nodes[node_block_id]["weight"] = 1
			node_successors_copy = list(nx_icfg.successors(node))
			for node_success in node_successors_copy:
				edgelist.append([node_block_id, node_success._block_id])
			nodes_to_be_analyzed.extend(node_successors_copy)
  
	sorted_edgelist = sorted(edgelist, key=lambda x: x[0])
	NCFG.add_edges_from(sorted_edgelist)
	dir_base_path = config.get_wfg_dir()
	if config.get_dappScan():
		dir_base_path = config.get_dapp_graph_dir(dir_base_path, function_name)
	dot_file_path = dir_base_path + "/" + function_name + "_wfg.dot"
	if not os.path.exists(dir_base_path):
		os.makedirs(dir_base_path)
	store_wfg(NCFG, dot_file_path)

	if config.get_scale():
		return

	graph_dot_file_path = dir_base_path + "/" + function_name + "_graph_wfg.dot"
	with open(graph_dot_file_path, 'w', encoding='utf8') as fp:
		nx.drawing.nx_pydot.write_dot(NCFG, fp)
	(dot_graph, ) = pydot.graph_from_dot_file(graph_dot_file_path)
	for i, node in enumerate(dot_graph.get_nodes()):
		node.set_shape('box')

	png_file_path = dir_base_path + "/" + function_name + "_wfg.png"
	dot_graph.write_png(png_file_path)