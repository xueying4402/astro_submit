from dapp_dependency import *
import sys
from lib.call_contractlint import *
from lib import arg_parser
from lib.timing_decorator import *
from lib.csv_manage import *
from lib import config
from dataset.dapp_deplicate_remove import main as dapp_deplicate_remove

def dapp_dir_filter(dapp_dir):
    dappname_files = os.listdir(dapp_dir)
    filtered_dappname_files = [file for file in dappname_files if not (file.endswith(".zip") or file.endswith(".pdf"))]
    return filtered_dappname_files

def dapp_compile(dapp_dir, **kwargs):
    dappname_files = dapp_dir_filter(dapp_dir)
    dapp_github_dirs = []
    dapp_github_files = []
    leaf_nodes = []
    for dappname_file in dappname_files:
        complete_path = os.path.join(dapp_dir, dappname_file)
        if os.path.isdir(complete_path):
            if dappname_file == "node_modules":
                os.chdir(complete_path)
            else:
                dapp_github_dirs.append(complete_path)
        elif os.path.isfile(complete_path) and dappname_file.endswith(".sol"):
            leaf_nodes.append(complete_path)
        else:
            raise RuntimeError("dapp error")
    for dapp_github_dir in dapp_github_dirs:
        node_list = getLeafNode(dapp_github_dir)
        for path, outDegree in node_list.items():
            if outDegree == 0:
                leaf_nodes.append(path)
    cmds = []
    _, dapp_name = os.path.split(dapp_dir)
    kwargs["output"] = os.path.join(kwargs["output"], dapp_name)
    for leaf_node in leaf_nodes:
        kwargs["contract"] = leaf_node
        cmd = collect_kwargs(**kwargs)
        cmds.append(cmd)
    call_contractlints(cmds)
    return dapp_dir

@timing_decorator
def dapp_compiles(**kwargs):
    dataset_dir = kwargs.get("setdir", None)
    if dataset_dir == None:
        raise RuntimeError("dapp error")
    error_log_basepath = kwargs.get("output", None)
    if not error_log_basepath:
        raise RuntimeError("dapp error")
    dapp_dirs = os.listdir(dataset_dir)
    compile_dapp_dirs = []
    for dapp_name in dapp_dirs:
        dapp_dir = os.path.join(dataset_dir, dapp_name)
        compile_dapp_dirs.append(dapp_dir)
    with ProcessPoolExecutor(max_workers=config.DOUBLE_MAX_WORKER) as executor:
        all_task = (executor.submit(dapp_compile, row, **kwargs) for row in compile_dapp_dirs)
        
        for task in as_completed(all_task):
            try:
                data = task.result()
            except Exception as e:
                data = e
            finally:
                print("dapp completed: ", data)

    error_log_path = os.path.join(error_log_basepath, "log")
    error_log_merged_file = os.path.join(error_log_path, "merged_error_log.csv")
    merge_error_logs(error_log_path, error_log_merged_file)
    
    print(f"***************************************deplicate_remove******************************")
    print(f"error log basepath: {error_log_basepath}")
    dapp_deplicate_remove(error_log_basepath)

if __name__ == "__main__":
    args = arg_parser.parse_args()
    kwargs = vars(args)
    dapp_compiles(**kwargs)