import re
import argparse
import os
import copy


class BatchDeobfuscator:

    def __init__(self):
        self.variables = {}
        self.exec_cmd = []
        for env_var, value in os.environ.items():
            self.variables[env_var.lower()] = value

    def read_logical_line(self, path):
        with open(path, 'r', encoding='utf-8') as input_file:
            logical_line = ''
            for line in input_file:
                if not line.endswith('^'):
                    logical_line += line
                    yield logical_line
                    logical_line = ''
                else:
                    logical_line += line + '\n'

    def get_commands(self, logical_line):
        state = 'init'
        counter = 0
        start_command = 0
        for char in logical_line:
            if state == 'init':  # init state
                if char == '"':  # quote is on
                    state = 'str_s'
                elif char == '^':
                    state = 'escape'
                elif char == '&' or char == '|':
                    yield logical_line[start_command: counter].strip()
                    start_command = counter + 1
            elif state == 'str_s':
                if char == '"':
                    state = 'init'
            elif state == 'escape':
                state = 'init'

            counter += 1

        last_com = logical_line[start_command:].strip()
        if last_com != "":
            yield last_com

    def get_value(self, variable):

        str_substitution = r"%\s*(?P<variable>[A-Za-z0-9#$'()*+,-.?@\[\]_`{}~ ]+)" \
                           r"(:~\s*(?P<index>[+-]?\d+)\s*,\s*(?P<length>[+-]?\d+)\s*)?%"

        matches = re.finditer(str_substitution, variable, re.MULTILINE)

        value = ''

        for matchNum, match in enumerate(matches):
            if len(match.groups()) == 4:
                var_name = match.group('variable').lower()
                if var_name in self.variables:
                    value = self.variables[var_name]
                    if match.group('index') is not None:
                        index = int(match.group('index'))
                        length = int(match.group('length'))
                        if length >= 0:
                            value = value[index: index + length]
                        else:
                            value = value[index: length]
                else:
                    # if variable name is not set, return the variable
                    value = variable

        return value

    def interpret_command(self, normalized_comm):

        normalized_comm = normalized_comm.strip()
        # remove paranthesis

        index = 0
        last = len(normalized_comm) - 1
        while index < last and (normalized_comm[index] == ' ' or normalized_comm[index] == '('):
            if normalized_comm[index] == '(':
                while last > index and (normalized_comm[last] == ' ' or normalized_comm[last] == ')'):
                    if normalized_comm[last] == ')':
                        last -= 1
                        break
                    last -= 1
            index += 1
        normalized_comm = normalized_comm[index:last + 1]

        if normalized_comm.lower().startswith('cmd'):
            set_command = r"\s*(call)?cmd(.exe)?\s*((\/A|\/U|\/Q|\/D)\s+|((\/E|\/F|\/V):(ON|OFF))\s*)*(\/c|\/r)\s*(?P<cmd>.*)"
            match = re.search(set_command, normalized_comm, re.IGNORECASE)
            if match is not None and match.group('cmd') is not None:
                cmd = match.group('cmd').strip('"')
                self.exec_cmd.append(cmd)

        else:
            # interpreting set command
            set_command = r"(\s*(call)?\s*set\s+\"?(?P<var>[A-Za-z0-9#$'()*+,-.?@\[\]_`{}~ ]+)=\s*(?P<val>[^\"\n]*)\"?)|" \
                          r"(\s*(call)?\s*set\s+/p\s+\"?(?P<input>[A-Za-z0-9#$'()*+,-.?@\[\]_`{}~ ]+)=[^\"\n]*\"?)"
            match = re.search(set_command, normalized_comm, re.IGNORECASE)
            if match is not None:
                if match.group('input') is not None:
                    self.variables[match.group('input')] = "__input__"
                else:
                    self.variables[match.group('var').lower()] = match.group('val')

    # pushdown automata
    def normalize_command(self, command):
        state = 'init'
        counter = 0
        normalized_com = ''

        stack = []
        for char in command:
            if state == 'init':  # init state
                if char == '"':  # quote is on
                    state = 'str_s'
                    normalized_com += char
                elif char == ',' or char == ';' or char == '\t':
                    # commas (",") are replaced by spaces, unless they are part of a string in doublequotes
                    # semicolons (";") are replaced by spaces, unless they are part of a string in doublequotes
                    # tabs are replaced by a single space
                    # http://www.robvanderwoude.com/parameters.php
                    normalized_com += ' '
                elif char == '^':  # next character must be escaped
                    state = 'escape'
                    stack.append('init')
                elif char == '%':  # variable start
                    variable_start = len(normalized_com)
                    normalized_com += '%'
                    stack.append('init')
                    state = 'var_s'
                elif char == '!':
                    variable_start = len(normalized_com)
                    normalized_com += '%'
                    stack.append('init')
                    state = 'var_s_2'
                else:
                    normalized_com += char
            elif state == 'str_s':
                if char == '"':
                    state = 'init'
                    normalized_com += char
                elif char == '%':
                    variable_start = len(normalized_com)
                    normalized_com += '%'
                    stack.append('str_s')
                    state = 'var_s'  # seen %
                elif char == '!':
                    variable_start = len(normalized_com)
                    normalized_com += '%'
                    stack.append('str_s')
                    state = 'var_s_2'  # seen !
                elif char == '^':
                    state = 'escape'
                    stack.append('str_s')
                else:
                    normalized_com += char
            elif state == 'var_s':
                if char == '%' and normalized_com[-1] != '%':
                    normalized_com += '%'
                    # print('<substring>{}</substring>'.format(command[variable_start:counter + 1]), end='')
                    value = self.get_value(normalized_com[variable_start:].lower())
                    normalized_com = normalized_com[:variable_start]
                    normalized_com += value
                    state = stack.pop()
                elif char == '%':
                    normalized_com += char
                    variable_start = counter
                elif char == '"':
                    if stack[-1] == 'str_s':
                        normalized_com += char
                        stack.pop()
                        state = 'init'
                    else:
                        normalized_com += char
                elif char == '^':
                    state = 'escape'
                    stack.append('var_s')
                else:
                    normalized_com += char
            elif state == 'var_s_2':
                if char == '!' and normalized_com[-1] != '%':
                    normalized_com += '%'
                    # print('<substring>{}</substring>'.format(command[variable_start:counter + 1]), end='')
                    value = self.get_value(normalized_com[variable_start:].lower())
                    normalized_com = normalized_com[:variable_start]
                    normalized_com += value
                    state = stack.pop()
                elif char == '!':
                    normalized_com += char
                    variable_start = counter
                elif char == '"':
                    if stack[-1] == 'str_s':
                        normalized_com += char
                        stack.pop()
                        state = 'init'
                    else:
                        normalized_com += char
                elif char == '^':
                    state = 'escape'
                    stack.append('var_s')
                else:
                    normalized_com += char
            elif state == 'escape':
                normalized_com += char
                state = stack.pop()

            counter += 1
        return normalized_com


def interpret_logical_line(deobfuscator, logical_line, tab=''):
    commands = deobfuscator.get_commands(logical_line)
    for command in commands:
        normalized_comm = deobfuscator.normalize_command(command)
        deobfuscator.interpret_command(normalized_comm)
        print(tab + normalized_comm)
        if len(deobfuscator.exec_cmd) > 0:
            print(tab + "[CHILE CMD]")
            for child_cmd in deobfuscator.exec_cmd:
                child_deobfuscator = copy.deepcopy(deobfuscator)
                child_deobfuscator.exec_cmd.clear()
                interpret_logical_line(child_deobfuscator, child_cmd, tab=tab + '\t')
            print(tab + "[END OF CHILE CMD]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, help="The path of obfuscated batch file")
    args = parser.parse_known_args()

    deobfuscator = BatchDeobfuscator()

    if args[0].file is not None:

        file_path = args[0].file

        for logical_line in deobfuscator.read_logical_line(args[0].file):
            interpret_logical_line(deobfuscator, logical_line)
    else:
        print("Please enter an obfuscated batch command:")
        interpret_logical_line(deobfuscator, input())
