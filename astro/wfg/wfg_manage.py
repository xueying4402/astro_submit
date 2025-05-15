from networkx.readwrite import json_graph
import networkx as nx

def graph2dict(graph):
	graph_dict = {}
	nodes = graph.nodes()
	edges = graph.edges()
	node_dict = {}
	for node_id in nodes: 
		node_dict[node_id] = graph.nodes[node_id]
	nodes_list = []
	for node in nodes:
		nodes_list.append(node)
	edges_list = []
	for edge in edges:
		edges_list.append([edge[0], edge[1]])
	graph_dict['nodes'] = nodes_list
	graph_dict['edges'] = edges_list
	graph_dict['node_dicts'] = node_dict
	return graph_dict


def dict2graph(line):
	graph = nx.MultiDiGraph() 
	graph_dict = eval(line)
	nodes = graph_dict['nodes']
	edges = graph_dict['edges']
	node_dict = graph_dict['node_dicts']
	
	graph.add_nodes_from(nodes) 
	graph.add_edges_from(edges) 
	for node_id in nodes: 
		graph.nodes[node_id].update(node_dict[node_id])
	return graph

def store_wfg(wfg, wfg_file):
	wfg_dict = graph2dict(wfg)
	with open(wfg_file, 'w') as fd:
		fd.write(repr(wfg_dict))

def load_wfg(wfg_file):
	try:
		with open(wfg_file, 'r') as fd:
			wfg_dict = fd.readline()
			wfg = dict2graph(wfg_dict)
			return wfg
	except Exception as e:
		return None