from concurrent.futures import ProcessPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED, as_completed
import subprocess
from lib import config
import shutil
import traceback
import sys
import csv
import os

def collect_kwargs(**kwargs):
    cmd = ["python", "/root/research/acinfer/acinfer/acinfer/analysis/contractlint.py"]
    for (key, value) in kwargs.items():
        if value:
            if key == "sname":
                cmd.extend(["--sname", value])
            elif key == "test":
                cmd.extend(["-tt"])
            elif key == "contract":
                cmd.extend(["-c", value])
            elif key == "output":
                cmd.extend(["-o", value])
            elif key == "icc":
                cmd.extend(["-icc", value])
            elif key == "mappingfpath":
                cmd.extend(["-mappingfpath", value])
            elif key == "graph":
                cmd.extend(["-dg"])
            elif key == "range":
                cmd.extend(["-r", value])
            elif key == "solver":
                cmd.extend(["-sv", value])
            elif key == "patterns":
                cmd.extend(["-p", value])
            elif key == "static":
                cmd.extend(["--static-only"])
            elif key == "owner_only":
                cmd.extend(["-oo"])
            elif key == "solc_path":
                cmd.extend(["--sc", value])
            elif key == "xblock":
                cmd.extend(["-xblock"])
            elif key == "xdir":
                cmd.extend(["-xdir", value])
            elif key == "contract_name":
                cmd.extend(["--contract-name", value])
            elif key == "XBlock_json":
                cmd.extend(["XBlock_json", value])
            elif key == "xblock":
                cmd.extend(["--xblock-json"])
            elif key == "prune":
                cmd.extend(["-prune"])
            elif key == "normalize":
                cmd.extend(["-normalize"])
            elif key == "scale":
                cmd.extend(["-scale"])
            elif key == "dappscan":
                cmd.extend(["-dappscan"])
            elif key == "csvdir":
                continue
            elif key == "setdir":
                continue
            elif key == "dataset_cve":
                continue
            elif key == "dataset_smartbugs":
                continue
            elif key == "chain":
                cmd.extend(["--chain", value])
            else:
                raise RuntimeError("wrong command-line parameter" + str(key))
    return cmd

def call_contractlints(cmds):
    error_completed = []
    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
        all_task = (executor.submit(call_contractlint,row) for row in cmds)
        
        for task in as_completed(all_task):
            try:
                data = task.result()
                if len(data) == 3 and data[0] == False:
                    if data[1].endswith(".sol"):
                        graph_dir_name = os.path.basename(data[1]).split(".sol")[0]
                        error_completed.append(graph_dir_name)
                    else:
                        error_completed.append(data[1])
            except Exception as e:
                data = e
            finally:
                if data:
                    print("contractlint completed: ", f"{data}")

def call_contractlint(cmd):
    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            executable=shutil.which(cmd[0]),
        ) as process:
            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(errors="backslashreplace"),
                stderr_bytes.decode(errors="backslashreplace"),
            )  # convert bytestrings to unicode strings
            if stderr:
                formatted_error = f"{stderr}"
                raise RuntimeError(formatted_error)
            return " ".join(cmd)
    except OSError as error:
        raise RuntimeError(error)
    except Exception as e:
        return False, cmd[3], e