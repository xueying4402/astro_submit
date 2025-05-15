import re

def remove_non_alnum(string):
    string = re.sub(r'\d*$', '', string)
    string = re.sub(r'[^a-zA-Z0-9]+', '', string)
    string = str.lower(string)
    return string

def invalid_name(title1, title2):
    if "multi" + title1 == title2 or "multi" + title2 == title1:
        return True
    return False
    invalid_checks = ["transfer", "div", "mod", "add", "sub", "mul", \
                       "get", "from", "of", "for", \
                        "safe", "only", "increase", "decrease", \
                        "whitelist", "or", "and", \
                        "check", "change", "set", "at", "by", "is"]
    invalid_prefix = []
    invalid_suffix = []

    if "update" + title1 in title2 or "update" + title2 in title1:
        return True
    if title1 + "with" in title2 or title2 + "with" in title1:
        return True
    if "get" + title1 in title2 or "get" + title2 in title1:
        return True
    for invalid_function in invalid_checks:
        if invalid_function in title1 or invalid_function in title2:
            return True
    return False

def candidates_nums(source_code, prefix):
    regex = re.escape(prefix)
    pattern = re.compile(regex)
    return len(pattern.findall(source_code))

def exist_call(title1, title2, func1, func2):
    body_pattern = r'\{([\s\S]*)\}'
    try:
        func1_body = re.search(body_pattern, func1).group()
        func2_body = re.search(body_pattern, func2).group()
    except:
        return True
    call_title1 = title1 + "\(((?!\)).)+\)"
    call_title2 = title2 + "\(((?!\)).)+\)"
    try:
        if re.search(call_title1, func1_body) or re.search(call_title2, func2_body):
            return True
    except:
        return True
    return False

def check_equal_nums(func1, func2):
    require_pattern = r"require\(((?!\);).)+\);"
    assert_pattern = r"assert\(((?!\);).)+\);"
    func1_checks = len(re.findall(require_pattern, func1)) + len(re.findall(assert_pattern, func1))
    func2_checks = len(re.findall(require_pattern, func2)) + len(re.findall(assert_pattern, func2))
    return (func1_checks, func2_checks)


def check_similar_function(func1, func2, contract_name, address, csv_to_write):
    title_pattern = r'function\s+(\w+)\s*\('
    if re.search("function\s?\(\)", func1) or re.search("function\s?\(\)", func2):
        return False
    try:
        title1 = re.search(title_pattern, func1).group(1)
        title2 = re.search(title_pattern, func2).group(1)
    except:
        csv_to_write.close()
        return False
    
    if exist_call(title1, title2, func1, func2):
        return False
    
    if not invalid_name(title1, title2):
        return False

    title1_letters = remove_non_alnum(title1)
    title2_letters = remove_non_alnum(title2)

    if title1_letters in title2_letters or title2_letters in title1_letters:
        func1_checks, func2_checks = check_equal_nums(func1, func2)
        if func1_checks != func2_checks:
            csv_to_write.write(address + "," +
                               contract_name + "," +
                               title1 + "," +
                               title2 + "," +
                               str(func1_checks) + "," +
                               str(func2_checks) + "\n")
            return True
    else:
        return False

if __name__ == "__main__":
    func1 = '''
        function tran1sferfrom(address operator, address from, uint256 tokenId, bytes memory) external returns (bytes4) {
            require(msg.sender == address(_positionManager()), "SNFT");
            require(_isStrategy(operator), "STR");
            // ...
        }
    '''

    func2 = '''
        function tran1sfer(address to) external nonReentrant returns (uint256[] memory collectedEarnings) {
            require(_isApprovedOrOwner(msg.sender), ExceptionsLibrary.APPROVED_OR_OWNER);
            // ...
        }
    '''
    check_similar_function(func1, func2, "...")  
