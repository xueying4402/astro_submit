import re
selected_kinds = ["ENTRYPOINT", "EXPRESSION", "RETURN", "IF",
                  "VARIABLE", "ASSEMBLY", "IFLOOP", "ENDIF",
                  "STARTLOOP",  "ENDLOOP", "THROW", "BREAK",
                  "CONTINUE", "PLACEHOLDER", "TRY", "CATCH",
                  "OTHER_ENTRYPOINT", "REVERT"
                  ]

all_kinds = selected_kinds

all_kinds_length = len(all_kinds)

symbols = ['-', '+', '*', '.', '[', ']', '(', ')', '{', '}', '*', '/', '=', '&', '!', '|', '<', '>', ';', ',', ':', '\'', '?', '#']

split_re = ''
for symbol in symbols: split_re = split_re + '\\'+symbol
split_re = '[\s' + split_re + ']'

def line_feature_index(line):
    global all_kinds
    for index in range(len(all_kinds)):
        items = re.split(split_re, line)
        if all_kinds[index] in items:
            return index
    return -1



