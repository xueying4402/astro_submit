import ast

import numpy
try:
	from wfg.config import *
except:
    from config import *

def obtain_node_feature(g, g_indexes, node_id):
	g_len = len(g_indexes)
	if node_id <= (g_len - 1):
		node = g_indexes[node_id]
		return g.nodes[node]["blk_vector"]
	else:
		return "dummy_node"

def node_ecul_sim(v1, v2):
	v1 = numpy.array(v1)
	v2 = numpy.array(v2)
	v1_norm = numpy.linalg.norm(v1)
	v2_norm = numpy.linalg.norm(v2)
	if v1_norm == 0 or v2_norm == 0:
		return 0
	dis = numpy.linalg.norm(v1 - v2)
	return 1.0-float(dis)/(v1_norm*v2_norm)

def node_cos_sim(vector1,vector2):
	dot_product = 0.0
	normA = 0.0
	normB = 0.0
	for a,b in zip(vector1,vector2):
		dot_product += a*b
		normA += a**2
		normB += b**2
	if normA == 0.0 or normB == 0.0:
		return 0   
	else:
		return dot_product / ((normA*normB)**0.5)
	
def obtain_node_weight(g, g_indexes, node_id):
	if not USE_WEIGHT:
		return 1.0
	g_len = len(g_indexes)
	if node_id <=(g_len - 1):
		node=g_indexes[node_id]
		return int(g.nodes[node]['weight'])
	else:
		return 1.0
	
def obtain_edge_feature(g, g_indexes, edge_id):
	g_len = len(g_indexes)
	if edge_id <= (g_len - 1):
		edge = g_indexes[edge_id]
		if 'blk_vector' in g.nodes[edge[0]]:
			src = g.nodes[edge[0]]['blk_vector']
		else:
			src = 'dummy_node'
		if 'blk_vector' in g.nodes[edge[1]]:
			dst = g.nodes[edge[1]]['blk_vector']
		else:
			dst = 'dummy_node'
		return (src, dst)
	else:
		return None #("dummy_node","dummy_node")
	
def obtain_edge_weight(g, g_indexes, edge_id):
	g_len = len(g_indexes)
	if edge_id <= (g_len - 1):
		edge = g_indexes[edge_id]
		#print 'obtain edge', edge
		if 'weight' in g.nodes[edge[0]]:
			src = g.nodes[edge[0]]['weight']
		else:
			src = 0
		if 'weight' in g.nodes[edge[1]]:
			dst = g.nodes[edge[1]]['weight']
		else:
			dst = 0
		return max(src, dst)
	else:
		return 0