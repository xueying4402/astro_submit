import json
import os

from lib.dic_and_file import *


def make_contract_file(source_code, file_name, contract_name):
    try:
        res = json.loads(source_code)
        for key in res:
            sol_file = open(
                file_name+"/"+key, 'w', encoding='UTF-8')
            sol_file.write(res[key]["content"])
            sol_file.close()
    except:
        if source_code[0] == source_code[1] == "{":
            new_code = source_code[1:-1]
            res = json.loads(new_code)
            sources = res["sources"]
            for name_a in sources:
                _dir, _file = os.path.split(
                    file_name+"/"+name_a)
                make_dir(_dir)
                sol_file = open(
                    file_name+"/"+name_a, 'w', encoding='UTF-8')
                sol_file.write(sources[name_a]["content"])
                sol_file.close()
        else:
            sol_file = open(file_name + "/" +
                            contract_name + ".sol", 'w', encoding='UTF-8')
            sol_file.write(source_code)
            sol_file.close()