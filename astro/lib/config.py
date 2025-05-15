import os

function_names = {}

TEST = False
is_Iblock_id = False
Iblock_id = 0
DEBUG = 0
DOUBLE_MAX_WORKER = 9
SINGLE_MAX_WORKER = 1

def set_function_name_pattern(function_name):
    set_pattern_name(function_name)
    function_pattern = "\n\s+function\s+" + "\w*" + function_name  + "\w*" + "\s*\(([^()]*)\)\s*([^()]*)\s*\(([^()]*)\)\s*\{((?!function).)+\}(?![;])"
    function_pattern_without_return = "\n\s+function\s+" + "\w*" + function_name  + "\w*" + "\s*\(([^()]*)\)\s*([^()]*)\s*\{((?!function).)+\}(?![;])"
    set_value("function_pattern", function_pattern)
    set_value("function_pattern_without_return", function_pattern_without_return)
    print("function_pattern change: ", function_pattern)
    
def get_function_pattern_with_return():
    return get_value("function_pattern")

def get_function_pattern_without_return():
    return get_value("function_pattern_without_return")

_global_dict = {}

def set_value(key, value):
    _global_dict[key] = value

def get_value(key):
    try:
        return _global_dict[key]
    except:
        return None

_global_dict["function_pattern"] = "\n\s+function\s+(\w+)\s*\(([^()]*)\)\s*([^()]*)\s*\(([^()]*)\)\s*\{((?!function).)+\}(?![;])"
_global_dict["function_pattern_without_return"] = "\n\s+function\s+(\w+)\s*\(([^()]*)\)\s*([^()]*)\s*\{((?!function).)+\}(?![;])"
_global_dict["prune"] = False
_global_dict["normalize"] = False
_global_dict["scale"] = False
_global_dict["dappscan"] = False
_global_dict["dataset_cve"] = False


def set_wfg_dir(wfg_dir):
    set_value("wfg_dir", wfg_dir)

def get_wfg_dir():
    return get_value("wfg_dir")

def set_dapp_relative_path(dapp_relative_path):
    set_value("dapp_relative_path", dapp_relative_path)

def get_dapp_relative_path():
    return get_value("dapp_relative_path")

def get_dapp_graph_dir(base_graph_dir, function_name):
    result_graph_dir = os.path.join(base_graph_dir, function_name)
    result_graph_dir = os.path.join(result_graph_dir, get_dapp_relative_path())
    if not os.path.exists(result_graph_dir):
        os.makedirs(result_graph_dir)
    return result_graph_dir

def set_pattern_name(function_name):
    set_value("pattern_name", str.lower(function_name))

def get_pattern_name():
    return get_value("pattern_name")

def skip_dump_file(function_name):
    # return False
    sname = get_pattern_name()
    if sname and sname not in str.lower(function_name):
        return True
    return False

def set_prune():
    set_value("prune", True)

def get_prune():
    return get_value("prune")

def set_normalize():
    set_value("normalize", True)

def get_normalize():
    return get_value("normalize")

def set_scale():
    set_value("scale", True)
    
def get_scale():
    return get_value("scale")

def set_dappScan():
    set_value("dappscan", True)

def reset_dappScan():
    set_value("dappscan", False)

def get_dappScan():
    return get_value("dappscan")

def set_dataset_cve():
    set_value("dataset_cve", True)
    
def get_dataset_cve():
    return get_value("dataset_cve")

def set_dataset_smartbugs():
    set_value("dataset_smartbugs", True)
    
def get_dataset_smartbugs():
    return get_value("dataset_smartbugs")

def set_dapp_target_contract(dapp_target_contract):
    set_value("dapp_target_contract", dapp_target_contract)
    
def get_dapp_target_contract():
    return get_value("dapp_target_contract")