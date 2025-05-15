# Readme

## Version Requirement

- python: python3.8

## Usage

### ACFG generation

-  Generating **ACFGs** for all functions that involve state modifications and are externally callable
- Input: solidity file
- Output: output_dir(indicated by `c`) contains the **ACFGs** for each function.

```shell
python acinfer/analysis/contractlint.py -c case/the_audited_database/0x0a0b34fc24b6a3477abc354eea9c9d8ae2c32132-Reputation.sol -o case_result/ -dg -scale -sn transferOwnership -prune -normalize
```

### Access control vulnerabilities detection

- output the detection results of access control vulnerabilities
- Input: directory path of **ACFGs**, the first path indicate the path of target contract and the second path indicate the path of the the_audited_database database
- Output: The result of access control vulnerabilities detection

```shell
python acinfer/find_candidate/sim.py case_result/ROIToken0xe48b75dc1b131fd3a8364b0580f76efd04cf6e9c case_result/0x0a0b34fc24b6a3477abc354eea9c9d8ae2c32132-Reputation
```