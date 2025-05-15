import os
import filecmp
import subprocess
import re
from concurrent.futures import ProcessPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED, as_completed
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wfg.wfgcmp import main as wfgcmp
import traceback
from lib import config
from lib.timing_decorator import timing_decorator
import csv
import json



def main(target_function_dir, root_directory, function_files, result_file):
    sim_result = False
    burn_dot_paths_dict = find_cmp_candidate_parallel(root_directory, function_files)
    # for filename, cmp_list in burn_dot_paths_dict.items():
    #     print(f"filename: {filename}\ncmp_list_length: {len(cmp_list)} cmp_list: {cmp_list}")
    burn_dot_paths_list = convert_dict_to_list(burn_dot_paths_dict, target_function_dir)
    
    function_sim_result_dict = {}


    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
        all_task = (executor.submit(wfgcmp, row[0], row[1]) for row in burn_dot_paths_list)

        for task in as_completed(all_task):
            try:
                data = task.result()
                if isinstance(data, list):
                    if data[1] in function_sim_result_dict:
                        function_sim_result_dict[data[1]].append(data)
                    else:
                        function_sim_result_dict[data[1]] = [data]
                else:
                    pass
            except Exception as exc:
                data = exc
                traceback.print_exc()
                sys.exit
            finally:
                pass
    
    for key, value in function_sim_result_dict.items():
        if len(value) % 2 == 0:
            sorted_value = sorted(value, key=lambda x: (-x[3], x[0]))[:-1]
        else:
            sorted_value = value
        false_count = len([x for x in sorted_value if x[0] == False])
        true_count = len([x for x in sorted_value if x[0] == True])
        if true_count > false_count:
            sim_result = True
            change_result_array_to_output_json(value, result_file)
            break
    
    print(f"target contract: {target_function_dir} sim result: {sim_result}")
    return sim_result

def convert_dict_to_list(paths_dict, target_function_dir):
    paths_list = []
    for function_name, paths in paths_dict.items():
        target_function_dot = os.path.join(target_function_dir, function_name)
        for path in paths:
            paths_list.append([target_function_dot, path])
    return paths_list

def find_cmp_candidate_parallel(root_directorys, function_files) -> dict:
    function_dot_2_burn_dot_paths_dict = {}
    if len(root_directorys) == 0:
        return function_dot_2_burn_dot_paths_dict
    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
        all_task = (executor.submit(find_cmp_candidate, root_directorys, row) for row in function_files)

        for task in as_completed(all_task):
            try:
                data = task.result()
                if len(data) == 2:
                    function_file, burn_dot_path_lists = data[0], data[1]
                    if isinstance(function_file, str) and isinstance(burn_dot_path_lists, list):
                        function_dot_2_burn_dot_paths_dict[function_file] = burn_dot_path_lists
                    else:
                        raise RuntimeError(f"reset id error")
                else:
                    raise RuntimeError(f"reset id error")
            except Exception as exc:
                data = exc
                traceback.print_exc()
                sys.exit
            finally:
                pass
    return function_dot_2_burn_dot_paths_dict
    
    
def find_cmp_candidate(root_directorys, function_file) -> dict:
    return find_cmp_candidate_real(root_directorys, function_file)

def find_cmp_candidate_real(root_directorys, function_file):
    burn_dot_paths = []
    target_function_name = str.lower(function_file)
    if target_function_name == "fallback_wfg.dot" or target_function_name == "fallback()_wfg.dot":
        return function_file, burn_dot_paths
    if target_function_name.endswith("_wfg.dot"):
        try:
            target_function_name = target_function_name.split("_wfg.dot")[0]
            target_function_name = re.sub(r'[^a-zA-Z]', '', target_function_name)
        except Exception as exc:
            print(f"{target_function_name} split error because: \n {exc}")
    if config.get_dappScan():
        if isinstance(root_directorys, str):
            pass
        else:
            raise RuntimeError(f"{root_directorys} is not str")
        functionname_directorys = os.listdir(root_directorys)
        for functionname_directory in functionname_directorys:
            if target_function_name in str.lower(functionname_directory):
                sub_root_directory = os.path.join(root_directorys, functionname_directory)
                for dirpath, dirnames, filenames in os.walk(sub_root_directory):
                    if dirpath != sub_root_directory:
                        for filename in filenames:
                            if not filename.endswith("_wfg.dot"):
                                continue
                            function_filename = filename.split("_wfg.dot")
                            try:
                                function_filename = str.lower(function_filename[0])
                                function_filename = re.sub(r'[^a-zA-Z]', '', function_filename)
                            except Exception as exc:
                                print(f"{target_function_name} split error because: \n {exc}")
                                
                            if target_function_name == function_filename:
                                burn_dot_path = os.path.join(dirpath, filename)
                                burn_dot_paths.append(burn_dot_path)
    else:
        filenames = os.listdir(root_directorys)
        for filename in filenames:
            if not filename.endswith("_wfg.dot"):
                continue
            function_filename = filename.split("_wfg.dot")
            try:
                function_filename = str.lower(function_filename[0])
                function_filename = re.sub(r'[^a-zA-Z]', '', function_filename)
            except Exception as exc:
                print(f"{target_function_name} split error because: \n {exc}")
                
            if target_function_name in function_filename:
                burn_dot_path = os.path.join(root_directorys, filename)
                burn_dot_paths.append(burn_dot_path)
    return function_file, burn_dot_paths

def find_cmp_candidate_single(root_directorys, function_files) -> dict:
    function_dot_2_burn_dot_paths_dict = {}
    if len(root_directorys) == 0:
        return function_dot_2_burn_dot_paths_dict
    for function_file in function_files:
        target_function_name = str.lower(function_file)
        if target_function_name.endswith("_wfg.dot"):
            try:
                target_function_name = target_function_name.split("_wfg.dot")[0]
            except Exception as exc:
                print(f"{target_function_name} split error because: \n {exc}")
        burn_dot_paths = []
        if config.get_dappScan():
            if isinstance(root_directorys, str):
                pass
            else:
                raise RuntimeError(f"{root_directorys} is not str")
            for dirpath, dirnames, filenames in os.walk(root_directorys):
                if dirpath != root_directorys:
                    for filename in filenames:
                        if not filename.endswith("_wfg.dot"):
                            continue
                        function_filename = filename.split("_wfg.dot")
                        if len(function_filename):
                            function_filename = str.lower(function_filename[0])
                        if target_function_name in function_filename:
                            burn_dot_path = os.path.join(dirpath, filename)
                            burn_dot_paths.append(burn_dot_path)
        else:
            for dirpath, dirnames, filenames in os.walk(root_directorys):
                if dirpath != root_directorys:
                    for filename in filenames:
                        if not filename.endswith("_wfg.dot"):
                            continue
                        function_filename = filename.split("_wfg.dot")
                        if len(function_filename):
                            function_filename = str.lower(function_filename[0])
                        if function_file in function_filename:
                            burn_dot_path = os.path.join(dirpath, filename)
                            burn_dot_paths.append(burn_dot_path)
        function_dot_2_burn_dot_paths_dict[function_file] = burn_dot_paths
    return function_dot_2_burn_dot_paths_dict

def change_result_array_to_output_json(input_array, file):
    result_dict = {}
    for item in input_array:
        key = item[1]
        result = {
            'result': item[0],
            'useful result': item[3],
            'another result': item[4]
        }
    if key in result_dict:
        # 合并compare字典
        result_dict[key][item[2]] =  result
    else:
        result_dict[key] = {item[2]: result}
    
    json.dump(result_dict, file, indent=4)
            

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python script.py target_function_dir root_directory")
        sys.exit(1)

    target_function_dir = sys.argv[1]
    root_directory = sys.argv[2]

    function_files = [
        file for file in os.listdir(root_directory) if file.endswith("_wfg.dot")
    ]

    result_csv_path = "compare_result.csv"
    with open(result_csv_path, "w", newline="") as result_file:
        main(target_function_dir, root_directory, function_files, result_file)