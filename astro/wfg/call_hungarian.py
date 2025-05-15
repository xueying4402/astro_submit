
import json
import re
import subprocess
import shutil
import os

import numpy as np

def call_hungarian(Metrix, arg_dir=None):
    row, column, metrix_str = from3to2(Metrix)
    command = ["python2.7", "/root/research/acinfer/acinfer/acinfer/wfg/python2/hungarian1.py", arg_dir]
    arg_str = str(row) + " " + str(column) + " " + metrix_str
    if not arg_dir:
        raise RuntimeError("error xdir file path")
    arg_arg_path = os.path.join(arg_dir, "arg.txt")
    with open(arg_arg_path, "w", encoding="utf-8") as file:
        file.write(arg_str)
    try:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            executable=shutil.which(command[0]),
        ) as process:
            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(errors="backslashreplace"),
                stderr_bytes.decode(errors="backslashreplace"),
            )  # convert bytestrings to unicode strings
            if stderr:
                raise RuntimeError("invoke error: ", stderr)
            arg_return_path = os.path.join(arg_dir, "return.txt")
            with open(arg_return_path, "r", encoding="utf-8") as file:
                return_str = file.read()
            lines = return_str.splitlines()
            if len(lines) == 1:
                file_contents = lines[0].strip()
                splitresult = file_contents.split(";")
            else:
                raise RuntimeError("return error" + arg_dir)
            mapping = fromstrtolist(int(splitresult[0]), int(splitresult[1]), splitresult[2])
            if len(mapping) == 0:
                raise RuntimeError("return error" + splitresult + arg_return_path + arg_dir)
            return mapping
    except OSError as error:
        raise RuntimeError(error)
    except Exception as e:
        raise RuntimeError(e)

def from3to2(metrix):
    row = len(metrix)
    column = len(metrix[0])
    metrix_str = ""
    for i in range(0, row):
        for j in range(0, column):
            metrix_str = metrix_str + str(metrix[i][j]) + ","
    return row, column, metrix_str[0: len(metrix_str) - 1]

def fromstrtolist(row, column, metrix_str):
      metrix_set = [int(node.strip()) for node in str.split(metrix_str, ",")]
      return np.array(metrix_set).reshape(row, column).tolist()

if __name__ == "__main__":
    metrix = [[0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.08482503578087186, 0.06820208177929055, 0.5, 0.513523138347365, 0.15377495513506234, 0.5, 1.0], [0.5, 0.0, 0.07822591691231034, 0.5, 0.5122022120425378, 0.16948788678091042, 0.5, 1.0], [0.5, 0.07822591691231034, 0.0, 0.5, 0.5015197708371077, 0.18321781899521272, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0], [0.5, 0.5122022120425378, 0.5015197708371077, 0.5, 0.0, 0.5386751345948129, 0.5, 1.0], [0.5, 0.16948788678091042, 0.18321781899521272, 0.5, 0.5386751345948129, 0.0, 0.5, 1.0], [0.0, 0.5, 0.5, 0.0, 0.5, 0.5, 0.0, 1.0]]
    mapping = call_hungarian(metrix)
    print("mapping: ", mapping)
