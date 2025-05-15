import sys
from crytic_compile.localize import config as compile_config
import argparse
import os
import logging
import sys
import glob
import copy
import time
import datetime
import json
import logging
import traceback
import multiprocessing
from slither.slither import Slither
from util import *
from detection import *
from callgraph import *
from lib import *
from shutil import rmtree
from state_var import *
import subprocess
from range_graph import *
from main_helper import *
from wfg.wfg import *
import pickle
from lib.arg_parser import *
from lib import config
from lib.timeout_decorator import timeout, set_timeout_contract, get_timeout_contract
from lib.csv_manage import *
import random


ETH_KEY = [
]
eth_key_length = len(ETH_KEY)

@timeout(600)
def analyze_contracts(contract_path, output_dir, dump_graph, **kwargs):
    try:
        dao = False
        tod = False
        contract_name = kwargs.get("contract_name", None)
        patterns = kwargs.get("patterns", "DAO")
        icc = kwargs.get("icc", False)
        solc_path = kwargs.get("solc_path", None)
        use_target_path = kwargs.get("actarget", False)
        chain_num = kwargs.get("chain", None)

        if use_target_path:
            target_path = kwargs.get("toutput", None)
            if not target_path:
                raise RuntimeError("missing target path: toutput")
            if contract_path.endswith(".sol"):
                graph_dir_name = os.path.basename(contract_path).split(".sol")[0]
            else:
                graph_dir_name = contract_path
            graph_dir = os.path.join(target_path, graph_dir_name)
            print("graph_dir: ", graph_dir)
            config.reset_dappScan()
        elif config.get_dappScan():
            graph_dir = os.path.dirname(output_dir)
            dapp_name = os.path.basename(output_dir)
            dapp_contract_name = os.path.basename(contract_path)
            dapp_contract_name = os.path.splitext(dapp_contract_name)[0]
            dapp_relative_path = os.path.join(dapp_name, dapp_contract_name)
            config.set_dapp_relative_path(dapp_relative_path)
        elif not compile_config.get_xblock():
            contract_name = os.path.basename(contract_path)
            info("Analysing started: %s" % contract_name)
            contract_name_without_ext = os.path.splitext(contract_name)[0]
            graph_dir = os.path.join(output_dir, contract_name_without_ext)
        else:
            graph_dir = os.path.join(output_dir, config.get_pattern_name())
            graph_dir = os.path.join(graph_dir, contract_path + contract_name)
            
        if (not config.get_dappScan()) and os.path.exists(graph_dir):
            shutil.rmtree(graph_dir)

        if (not config.get_dappScan()) and not os.path.exists(graph_dir):
            os.makedirs(graph_dir)
        config.set_wfg_dir(graph_dir)
        
        if config.get_dappScan():
            log_path = os.path.join(config.get_dapp_graph_dir(graph_dir, "log"), "contractlint.log")
        else:
            log_path = os.path.join(graph_dir, 'contractlint.log')
        
        if  use_target_path or config.get_dappScan():
            log = init_logging('analyzer.%s' % contract_path, log_path, file_mode='w', console=True)
        elif not compile_config.get_xblock():
            log = init_logging('analyzer.%s' % contract_name_without_ext, log_path, file_mode='w', console=True)
        else:
            log = init_logging('analyzer.%s' % contract_name, log_path, file_mode='w', console=True)

        # Record analysis start time
        now = datetime.datetime.now()
        analysis_start_time = now.strftime(DATE_FORMAT)
        if not config.get_scale():  log.info("address: %s" % contract_path)
        if not config.get_scale():  log.info('Analysis started at: %s' % analysis_start_time)
        start_time = time.time()


        # Get solc binary path
        if not contract_path.startswith("0x") and not compile_config.get_xblock() and not solc_path:
            _, solc_path = get_solc_path(contract_path, log)
            print("change to solc_path: ", solc_path)


        # Initialize Slither
        if DEBUG: start_t = time.time()
        # index = random.randint(1, 1000) % eth_key_length
        # api_key = ETH_KEY[index]
        api_key = ""
        try:
            if chain_num:
                contract_path = chain_num + ":" + contract_path
            slither_obj = Slither(contract_path, solc=solc_path, etherscan_api_key=api_key, **kwargs)
        except Exception as e:
            if (not contract_path.startswith("0x")) and (compile_config.get_xblock() or config.get_dappScan()):
                _, solc_path = get_solc_path(contract_path, log, use_solc_max=True)
                slither_obj = Slither(contract_path, solc=solc_path, etherscan_api_key=api_key, **kwargs)
            elif use_target_path:
                if contract_path.endswith(".sol"):
                    graph_dir_name = os.path.basename(contract_path).split(".sol")[0]
                    slither_obj = Slither(graph_dir_name, etherscan_api_key=api_key, **kwargs)
                else:
                    _, solc_path = get_solc_path(contract_path, log, use_solc_max=True)
                    slither_obj = Slither(contract_path, solc=solc_path, etherscan_api_key=api_key, **kwargs)
            else:
                traceback.print_exc()
                sys.exit(1)
        if DEBUG: end_t = time.time()
        if DEBUG: print("slither time: ", end_t - start_t)
        if DEBUG: start_t = time.time()
        target_contracts = get_child_contracts(slither_obj)

        # Generate callgraph
        if not config.get_scale():  log.info('Callgraph generation started!')
        callgraph = CallGraph(slither_obj, graph_dir, False, log)
        if not config.get_scale():  log.info('Callgraph generation finished!')

        # Build interprocedural cfg for all public functions
        if not config.get_scale():  log.info('Interprocedural CFG generation started!')
        generated_icfg, icfg_objects = generate_icfg(slither_obj, callgraph, graph_dir, dump_graph, log)
        if not config.get_scale():  log.info('Interprocedural CFG generation finished!')
        if DEBUG: end_t = time.time()
        if DEBUG: print("sailfish time: ", end_t - start_t)

        if DEBUG: start_t = time.time()
        if not config.get_scale():  log.info("WFG generation started")
        if not compile_config.get_xblock():
            wfg = code2wfg(slither_obj, generated_icfg, target_contracts)
        else:
            wfg = code2wfg(slither_obj, generated_icfg, target_contracts, address=contract_path)
        if not config.get_scale():  log.info("WFG generation finished")
        if DEBUG: end_t = time.time()
        if DEBUG: print("acinfer time: ", end_t - start_t)
        
        # Record analysis duration
        end_time = time.time()
        analysis_duration = end_time - start_time
        if not config.get_scale():  log.info('Static Analysis took %f seconds' % analysis_duration)


    except Exception as e:
        if compile_config.get_xblock():
            error_type = type(e).__name__
            error_traceback = traceback.format_exc()
            address = contract_path
            write_error_to_csv(graph_dir, error_type, error_traceback, address)
            sys.exit(1)
        if config.get_dappScan():
            error_type = type(e).__name__
            error_traceback = traceback.format_exc()
            address = contract_path
            write_error_to_csv(config.get_dapp_graph_dir(graph_dir, "log"), error_type, error_traceback, address)
            sys.exit(1)
        if use_target_path:
            raise RuntimeError(e)
        traceback.print_exc()
        sys.exit(1)
        



def graph(**kwargs):
    global TIMEOUT_CONTRACT
    # If it's a directory, analyze all the contracts in it
    dump_graph = False
    sname = kwargs.get("sname", None)

    if kwargs.get("xblock", None):
        compile_config.use_xblock()
        with open(kwargs["xdir"] + "/" + kwargs["contract_name"] + kwargs["contract"], "rb") as f:
            data = pickle.load(f)
            compile_config.set_xblock_json(data)
            
    if kwargs.get("scale", None):
        config.set_scale()

    if kwargs.get("test", 0):
        DEBUG = 1

    if kwargs.get("prune", True):
        config.set_prune()
        
    if kwargs.get("normalize", None):
        config.set_normalize()
    
    if kwargs.get("graph", None):
        dump_graph = True

    if kwargs.get("static", None):
        only_static = True
    
    if kwargs.get("owner_only", None):
        call_heuristic = True

    if kwargs.get("icc") and kwargs.get("mappingfpath", None) is not None:
        icc = True
    
    if kwargs.get("dappscan", None):
        config.set_dappScan()
        set_timeout_contract(kwargs["contract"])
    
    if sname:
        config.set_pattern_name(sname)
    
    if compile_config.get_xblock():
        contracts = [kwargs["contract"]]

    elif os.path.isdir(kwargs["contract"]):
        path = os.path.join(kwargs["contract"], "*.sol")
        contracts = glob.glob(path)
    
    # If it's a single contract, analyze it
    elif os.path.isfile(kwargs["contract"]):
        contracts = [kwargs["contract"]]
        
    elif kwargs["contract"] and kwargs["contract"].startswith("0x"):
        contracts = [kwargs["contract"]]

    else:
        print(kwargs["contract"])
        raise RuntimeError('Non existent contract or directory: %s' % kwargs["contract"])
        # sys.exit(1)

    config.set_dapp_target_contract(";".join(contracts))

    contracts_to_be_analyzed = []

    if len(contracts) > 1:
        for contract_path in contracts:
            contract_name = os.path.basename(contract_path)
            contracts_to_be_analyzed.append((contract_path, kwargs["output"], dump_graph), **kwargs)
    else:
        contract_path = contracts[0]


    # Analyze the contracts using mutiprocessing pool if number of contracts
    # is more than one
    if len(contracts) > 1:
        with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
            pool.starmap(analyze_contracts, contracts_to_be_analyzed)
        
        pool.join()
    
    else:
        analyze_contracts(contract_path, kwargs["output"], dump_graph, **kwargs)
    
def main():
    global contract_path
    args = parse_args()
    graph(**vars(args))

if __name__ == "__main__":
    main()
