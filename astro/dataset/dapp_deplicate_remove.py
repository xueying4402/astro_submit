import os
from concurrent.futures import ProcessPoolExecutor, wait, ALL_COMPLETED, FIRST_COMPLETED, as_completed
import sys
import traceback
from lib import config
from lib.timing_decorator import timing_decorator
from lib.timeout_decorator import timeout, set_timeout_dirpath
from wfg.wfgcmp import main as wfgcmp
import shutil

def main(root_directory):
    if len(root_directory) == 0:
        raise RuntimeError(f"dappscan_classfier{root_directory} is empty")
    function_directories = os.listdir(root_directory)
    with ProcessPoolExecutor(max_workers=config.SINGLE_MAX_WORKER) as executor:
            all_task = (executor.submit(function_directory_deplicate_remove, root_directory, row) for row in function_directories)

            for task in as_completed(all_task):
                try:
                    data = task.result()
                    if len(data) == 4:
                        print(f"dir: {data[0]}, origin: {data[1]}, remain: {data[2]}, full_append: {data[3]}")
                    else:
                        raise RuntimeError(f"return error： {data}")
                except Exception as exc:
                    data = exc
                    print(f"RuntimeError: function directory deplicate remove: {data}")
                finally:
                    pass

def function_directory_deplicate_remove(root_directory, function_directory):
    set_timeout_dirpath(os.path.join(root_directory, function_directory))
    return function_directory_deplicate_remove_real(root_directory, function_directory)

@timeout(3000)
def function_directory_deplicate_remove_real(root_directory, function_directory):
    function_directory = "calcInvariantStable"
    cmp_filepaths = []
    if isinstance(function_directory, str):
        pass
    else:
        raise RuntimeError(f"{function_directory} is not str")
    directory_functionname = str.lower(function_directory)
    abs_function_directory = os.path.join(root_directory, function_directory)
    functionname_directorys = os.listdir(abs_function_directory)
    for functionname_directory in functionname_directorys:
        sub_root_directory = os.path.join(abs_function_directory, functionname_directory)
        for dirpath, dirnames, filenames in os.walk(sub_root_directory):
            if dirpath != sub_root_directory:
                for filename in filenames:
                    if not filename.endswith("_wfg.dot"):
                        continue
                    function_filename = filename.split("_wfg.dot")
                    if len(function_filename):
                        function_filename = str.lower(function_filename[0])
                    if directory_functionname in function_filename:
                        cmp_file = os.path.join(dirpath, filename)
                        cmp_filepaths.append(cmp_file)
    if len(cmp_filepaths) == 0:
        if function_directory not in ["log", "slitherConstructorVariables", "slitherConstructorConstantVariables"]:
            print(f"cmp_fliepath Error {abs_function_directory} has no cmp_filepaths")
        else:
            print(f"cmp_fliepath Normal {abs_function_directory} has no cmp_filepaths")
    unique_filepaths = []
    isFull = False
    full_append = 0
    for cmp_filepath in cmp_filepaths:
        isUnique = True
        if isFull:
            unique_filepaths.append(cmp_filepath)
            full_append += 1
            continue
        
        for unique_filepath in unique_filepaths:
            sim_result = wfgcmp(cmp_filepath, unique_filepath, isdeplicate=True)
            if sim_result == 1:
                isUnique = False
                cmp_dirpath = os.path.dirname(cmp_filepath)
                shutil.rmtree(cmp_dirpath)
                break
        if isUnique:
            unique_filepaths.append(cmp_filepath)
        
        if len(unique_filepaths) == 100:
            isFull = True
    return abs_function_directory, len(cmp_filepaths), len(unique_filepaths), full_append
            
if __name__ == "__main__":
    main("/home/liwei/acinfer/labelcodeclassfier")