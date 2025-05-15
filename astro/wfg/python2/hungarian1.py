# -*- coding: utf-8 -*-
from __future__	 import division
import json
import sys
import numpy as np
import os

try:
	import hungarian as hungarian1
except Exception, e:
	import hungarian as hungarian1

def call_hungarian(Metrix, arg_dir):
    mapping = hungarian1.lap(Metrix)
    row, column, mapping = from3to2(mapping)
    arg_return_dir = os.path.join(arg_dir, "return.txt")
    with open(arg_return_dir, "w") as f:
        f.write(str(row) + ";" + str(column) + ";" + mapping)

def fromstrtolist(row, column, metrix_str):
      metrix_set = [float(node.strip()) for node in str.split(metrix_str, ",")]
      return np.array(metrix_set).reshape(row, column).tolist()

def from3to2(metrix):
    row = len(metrix)
    column = len(metrix[0])
    metrix_str = ""
    for i in range(0, row):
        for j in range(0, column):
            metrix_str = metrix_str + str(metrix[i][j]) + ","
    return row, column, metrix_str[0: len(metrix_str) - 1]

if __name__ == "__main__":
    # metrix = [[0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.08482503578087186, 0.06820208177929055, 0.5, 0.513523138347365, 0.15377495513506234, 0.5, 1.0], [0.5, 0.0, 0.07822591691231034, 0.5, 0.5122022120425378, 0.16948788678091042, 0.5, 1.0], [0.5, 0.07822591691231034, 0.0, 0.5, 0.5015197708371077, 0.18321781899521272, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.5122022120425378, 0.5015197708371077, 0.5, 0.0, 0.5386751345948129, 0.5, 1.0], [0.5, 0.16948788678091042, 0.18321781899521272, 0.5, 0.5386751345948129, 0.0, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0]]
    # metrix_str = "[[0.0,', '0.5,', '0.5,', '0.0,', '0.5,', '0.5,', '0.0,', '1.0],', '[0.5,', '0.08482503578087186,', '0.06820208177929055,', '0.5,', '0.513523138347365,', '0.15377495513506234,', '0.5,', '1.0],', '[0.5,', '0.0,', '0.07822591691231034,', '0.5,', '0.5122022120425378,', '0.16948788678091042,', '0.5,', '1.0],', '[0.5,', '0.07822591691231034,', '0.0,', '0.5,', '0.5015197708371077,', '0.18321781899521272,', '0.5,', '1.0],', '[0.0,', '0.5,', '0.5,', '0.0,', '0.5,', '0.5,', '0.0,', '1.0],', '[0.5,', '0.5122022120425378,', '0.5015197708371077,', '0.5,', '0.0,', '0.5386751345948129,', '0.5,', '1.0],', '[0.5,', '0.16948788678091042,', '0.18321781899521272,', '0.5,', '0.5386751345948129,', '0.0,', '0.5,', '1.0],', '[0.0,', '0.5,', '0.5,', '0.0,', '0.5,', '0.5,', '0.0,', '1.0]]"
    # metrix_str = json.dumps(metrix)
    arg_dir = sys.argv[1]
    arg_arg_path = os.path.join(arg_dir, "arg.txt")
    with open(arg_arg_path, "r") as file:
        file_contents = file.read()
    lines = file_contents.splitlines()
    if len(lines) == 1:
        file_contents = lines[0].strip()
        
        words = file_contents.split(" ")
        row, column, metrix_str = int(words[0]), int(words[1]), words[2]
    else:
        raise RuntimeError("arg file content error: " + arg_dir + " file lines: " + str(len(lines)) + "\n" + "path: ", lines)
    call_hungarian(fromstrtolist(row, column, metrix_str), arg_dir)

