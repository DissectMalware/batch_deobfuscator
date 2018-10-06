import re
import argparse

class BatchDeobfuscator:

    def __init__(self):
        self.variables = {}

    def read_logical_line(self, path):
        with open(path, 'r') as input_file:
            logical_line = ''
            for line in input_file:
                if not line.endswith('^'):
                    logical_line += line
                    yield logical_line
                    logical_line = ''
                else:
                    logical_line += line+'\n'



    def get_commands(self, logical_line):
        command_splitor_rule = '[^^](\^\^)*(?P<comm_splitor>[&|])'
        command_splitor_re = re.compile(command_splitor_rule)
        index = -1
        previous = 0
        while True:
            matched =command_splitor_re.search(logical_line, pos= index)
            if matched is None:
                yield logical_line[index+1: ]
                break
            else:
                index = matched.regs[0][1]
                yield logical_line[previous:index-1]
                previous=index


    def get_value(self, variable):

        str_substitution = r"%\s*(?P<variable>[A-Za-z0-9#$'()*+,-.?@\[\]_`{}~ ]+)(:~\s*(?P<index>[+-]?\d+)\s*,\s*(?P<length>[+-]?\d+)\s*)?%"

        matches = re.finditer(str_substitution, variable, re.MULTILINE)

        value = ''

        for matchNum, match in enumerate(matches):
            if len(match.groups()) == 4:
                variable = match.group('variable').lower()
                if match.group('index') is not None:
                    index= int(match.group('index'))
                    length = int(match.group('length'))
                    value = self.variables.setdefault(variable, '')
                    # TODO: handle negative values
                    value = value[index: index + length]
                else:
                    value = self.variables.setdefault(variable, '')

        return value


    def interpret_command(self, normalized_comm):

        # interpreting set command
        normalized_comm = normalized_comm.strip()
        set_command = r"\s*set\s+(?P<var>[A-Za-z0-9#$'()*+,-.?@\[\]_`{}~ ]+)=\s*(?P<val>(\".*\")|\S+)|" \
                      r"(\s*set\s+/p\s+(?P<input>[A-Za-z0-9#$'()*+,-.?@\[\]_`{}~ ]+)=.*)"
        matches = re.finditer(set_command, normalized_comm, re.IGNORECASE)
        for matchNum, match in enumerate(matches):
            if match.group('input') is not None:
                self.variables[match.group('input')] = "__input__"
            else:
                self.variables[match.group('var').lower()] = match.group('val')




    def normalize_command(self, command):
        quote_on = False
        state = 'init'
        counter = 0
        normalized_com = ''
        for char in command:
            if state == 'init':  # init state
                if char == '"':   # quote is on
                    state = 'str_s'
                    normalized_com += char
                elif char == '^':  # next character must be escaped
                    state = 'escape'
                elif char == '%':    # variable start
                    state = 'init_var_s'
                    variable_start = counter
                else:
                    normalized_com +=char
            elif state == 'str_s':
                if char == '"':
                    state = 'init'
                    normalized_com += char
                elif char == '%':
                    variable_start = counter
                    state = 'var_s' #seen %
                else:
                    normalized_com += char
            elif state == 'var_s':
                if char =='%' and counter - variable_start > 1:
                    # print('<substring>{}</substring>'.format(command[variable_start:counter + 1]), end='')
                    normalized_com += self.get_value(command[variable_start:counter + 1].lower())
                    state = 'str_s'
                elif char =='%':
                    normalized_com += char
                    variable_start = counter
                elif char == '"':
                    normalized_com += char
                    state = 'init'
            elif state == 'init_var_s' :
                if char =='%' and counter - variable_start > 1:
                    # print('<substring>{}</substring>'.format(command[variable_start:counter + 1]), end='')
                    normalized_com += self.get_value(command[variable_start:counter + 1].lower())
                    state = 'init'
                elif char =='%':
                    normalized_com += char
                    variable_start = counter
                elif char == '"':
                    state = 'str_s'
            elif state == 'escape':
                normalized_com += char
                state = 'init'

            counter += 1
        return normalized_com




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file",  type=str, help="The path of obfuscated batch file", required=True)
    args = parser.parse_known_args()

    if args[0].file is not None:

        file_path = args[0].file

        deobfuscator = BatchDeobfuscator()

        for logical_line in deobfuscator.read_logical_line(args[0].file):
            commands = deobfuscator.get_commands(logical_line)
            for command in commands:
                normalized_comm = deobfuscator.normalize_command(command )
                deobfuscator.interpret_command(normalized_comm)
                print(normalized_comm)