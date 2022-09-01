import argparse
import base64
import copy
import hashlib
import os
import re
import shlex
import shutil
import string
import tempfile
from collections import defaultdict
from urllib.parse import urlparse

QUOTED_CHARS = ["|", ">", "<", '"', "^", "&"]

# Powershell detection
ENC_RE = rb"(?i)(?:-|/)e(?:c|n(?:c(?:o(?:d(?:e(?:d(?:c(?:o(?:m(?:m(?:a(?:nd?)?)?)?)?)?)?)?)?)?)?)?)?$"
PWR_CMD_RE = rb"(?i)(?:-|/)c(?:o(?:m(?:m(?:a(?:nd?)?)?)?)?)?$"

# Gathered from https://gist.github.com/api0cradle/8cdc53e2a80de079709d28a2d96458c2
RARE_LOLBAS = [
    "forfiles",
    "bash",
    "scriptrunner",
    "syncappvpublishingserver",
    "hh.exe",
    "msbuild",
    "regsvcs",
    "regasm",
    "installutil",
    "ieexec",
    "msxsl",
    "odbcconf",
    "sqldumper",
    "pcalua",
    "appvlp",
    "runscripthelper",
    "infdefaultinstall",
    "diskshadow",
    "msdt",
    "regsvr32",
]


class BatchDeobfuscator:
    def __init__(self, complex_one_liner_threshold=4):
        self.variables = {}
        self.exec_cmd = []
        self.exec_ps1 = []
        self.traits = defaultdict(list)
        self.complex_one_liner_threshold = complex_one_liner_threshold
        if os.name == "nt":
            for env_var, value in os.environ.items():
                self.variables[env_var.lower()] = value
        # fake it till you make it
        else:
            self.variables = {
                "allusersprofile": "C:\\ProgramData",
                "appdata": "C:\\Users\\puncher\\AppData\\Roaming",
                "commonprogramfiles": "C:\\Program Files\\Common Files",
                "commonprogramfiles(x86)": "C:\\Program Files (x86)\\Common Files",
                "commonprogramw6432": "C:\\Program Files\\Common Files",
                "computername": "MISCREANTTEARS",
                "comspec": "C:\\WINDOWS\\system32\\cmd.exe",
                "driverdata": "C:\\Windows\\System32\\Drivers\\DriverData",
                "errorlevel": "0",  # Because nothing fails.
                "fps_browser_app_profile_string": "Internet Explorer",
                "fps_browser_user_profile_string": "Default",
                "homedrive": "C:",
                "homepath": "\\Users\\puncher",
                "java_home": "C:\\Program Files\\Amazon Corretto\\jdk11.0.7_10",
                "localappdata": "C:\\Users\\puncher\\AppData\\Local",
                "logonserver": "\\\\MISCREANTTEARS",
                "number_of_processors": "4",
                "onedrive": "C:\\Users\\puncher\\OneDrive",
                "os": "Windows_NT",
                "path": (
                    "C:\\Program Files\\Amazon Corretto\\jdk11.0.7_10\\bin;C:\\WINDOWS\\system32;"
                    "C:\\WINDOWS;C:\\WINDOWS\\System32\\Wbem;C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\;"
                    "C:\\Program Files\\dotnet\\;C:\\Program Files\\Microsoft SQL Server\\130\\Tools\\Binn\\;"
                    "C:\\Users\\puncher\\AppData\\Local\\Microsoft\\WindowsApps;"
                    "%USERPROFILE%\\AppData\\Local\\Microsoft\\WindowsApps;"
                ),
                "pathext": ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC",
                "processor_architecture": "AMD64",
                "processor_identifier": "Intel Core Ti-83 Family 6 Model 158 Stepping 10, GenuineIntel",
                "processor_level": "6",
                "processor_revision": "9e0a",
                "programdata": "C:\\ProgramData",
                "programfiles": "C:\\Program Files",
                "programfiles(x86)": "C:\\Program Files (x86)",
                "programw6432": "C:\\Program Files",
                "psmodulepath": "C:\\WINDOWS\\system32\\WindowsPowerShell\\v1.0\\Modules\\",
                "public": "C:\\Users\\Public",
                "random": "4",  # https://xkcd.com/221/
                "sessionname": "Console",
                "systemdrive": "C:",
                "systemroot": "C:\\WINDOWS",
                "temp": "C:\\Users\\puncher\\AppData\\Local\\Temp",
                "tmp": "C:\\Users\\puncher\\AppData\\Local\\Temp",
                "userdomain": "MISCREANTTEARS",
                "userdomain_roamingprofile": "MISCREANTTEARS",
                "username": "puncher",
                "userprofile": "C:\\Users\\puncher",
                "windir": "C:\\WINDOWS",
                "__compat_layer": "DetectorsMessageBoxErrors",
            }

        # There are 211 lines coming out of curl --help, so I won't be parsing all the options
        self.curl_parser = argparse.ArgumentParser()
        self.curl_parser.add_argument("-o", "--output", dest="output", help="Write to file instead of stdout")
        self.curl_parser.add_argument(
            "-O",
            "--remote-name",
            dest="remote_name",
            action="store_true",
            help="Write output to a file named as the remote file",
        )
        self.curl_parser.add_argument("url", help="URL")
        # Patch all possible one-character arguments
        for char in string.ascii_letters + string.digits + "#:":
            try:
                self.curl_parser.add_argument(f"-{char}", action="store_true")
            except argparse.ArgumentError:
                pass

    def read_logical_line(self, path):
        with open(path, "r", encoding="utf-8", errors="ignore") as input_file:
            logical_line = ""
            for line in input_file:
                if not line.endswith("^"):
                    logical_line += line
                    yield logical_line
                    logical_line = ""
                else:
                    logical_line += line + "\n"

    def split_if_statement(self, statement):
        if_statement = (
            r"(?P<conditional>(?P<if_statement>if)\s+(not\s+)?"
            r"(?P<type>errorlevel\s+\d+\s+|exist\s+(\".*\"|[^\s]+)\s+|.+?==.+?\s+|"
            r"(\/i\s+)?[^\s]+\s+(equ|neq|lss|leq|gtr|geq)\s+[^\s]+\s+|cmdextversion\s+\d\s+|defined\s+[^\s]+\s+)"
            r"(?P<open_paren>\()?)(?P<true_statement>[^\)]*)(?P<close_paren>\))?"
            r"(\s+else\s+(\()?\s*(?P<false_statement>[^\)]*)(\))?)?"
        )
        match = re.search(if_statement, statement, re.IGNORECASE)
        if match is not None:
            conditional = match.group("conditional")
            if match.group("open_paren") is None:
                conditional = f"{conditional}("
            yield conditional
            yield match.group("true_statement")
            if match.group("false_statement") is None:
                if match.group("open_paren") is None or match.group("close_paren") is not None:
                    yield ")"
            else:
                # Got an ELSE statement
                if match.group("if_statement") == "if":
                    yield ") else ("
                else:
                    yield ") ELSE ("
                yield match.group("false_statement")
                yield ")"
        else:
            # Broken statement, maybe a re-run
            yield statement

    def split_for_statement(self, statement):
        for_statement = (
            r"(?P<loop>(?P<for_statement>for)\s+"
            r"(?P<parameter>.+)"
            r"\s+IN\s+\((?P<in_set>[^\)]+)\)"
            r"\s+DO\s+"
            r"(?P<open_paren>\()?)(?P<command>[^\)]*)(?P<close_paren>\))?"
        )
        match = re.search(for_statement, statement, re.IGNORECASE)
        if match is not None:
            loop = match.group("loop")
            if match.group("open_paren") is None:
                loop = f"{loop}("
            yield loop
            yield match.group("command")
            if match.group("open_paren") is None or match.group("close_paren") is not None:
                yield ")"
        else:
            # Broken statement, maybe a re-run
            yield statement

    def get_commands_special_statement(self, statement):
        if statement.lower().startswith("if "):
            for part in self.split_if_statement(statement):
                if part.strip() != "":
                    yield part
        elif statement.lower().startswith("for "):
            for part in self.split_for_statement(statement):
                if part.strip() != "":
                    yield part
        else:
            yield statement

    def get_commands(self, logical_line):
        state = "init"
        counter = 0
        start_command = 0
        for char in logical_line:
            # print(f"C:{char}, S:{state}")
            if state == "init":  # init state
                if char == '"':  # quote is on
                    state = "str_s"
                elif char == "^":
                    state = "escape"
                elif char == "&" and logical_line[counter - 1] == ">":
                    # Usually an output redirection, we want to keep it on the same line
                    pass
                elif char == "&" or char == "|":
                    cmd = logical_line[start_command:counter].strip()
                    if cmd != "":
                        for part in self.get_commands_special_statement(cmd):
                            yield part
                    start_command = counter + 1
            elif state == "str_s":
                if char == '"':
                    state = "init"
            elif state == "escape":
                state = "init"

            counter += 1

        last_com = logical_line[start_command:].strip()
        if last_com != "":
            for part in self.get_commands_special_statement(last_com):
                yield part

    def get_value(self, variable):

        str_substitution = (
            r"([%!])(?P<variable>[\"^|!\w#$'()*+,-.?@\[\]`{}~\s+]+)"
            r"("
            r"(:~\s*(?P<index>[+-]?\d+)\s*(?:,\s*(?P<length>[+-]?\d+))?\s*)|"
            r"(:(?P<s1>[^=]+)=(?P<s2>[^=]*))"
            r")?(\1)"
        )

        matches = re.finditer(str_substitution, variable, re.MULTILINE)

        value = ""

        for matchNum, match in enumerate(matches):
            var_name = match.group("variable").lower()
            if var_name in self.variables:
                value = self.variables[var_name]
                if match.group("index") is not None:
                    index = int(match.group("index"))
                    if index < 0 and -index >= len(value):
                        index = 0
                    elif index < 0:
                        index = len(value) + index
                    if match.group("length") is not None:
                        length = int(match.group("length"))
                    else:
                        length = len(value) - index
                    if length >= 0:
                        value = value[index : index + length]
                    else:
                        value = value[index:length]
                elif match.group("s1") is not None:
                    s1 = match.group("s1")
                    s2 = match.group("s2")
                    if s1.startswith("*") and s1[1:].lower() in value.lower():
                        value = f"{s2}{value[value.lower().index(s1[1:].lower())+len(s1)-1:]}"
                    else:
                        pattern = re.compile(re.escape(s1), re.IGNORECASE)
                        value = pattern.sub(re.escape(s2), value)
            else:
                # It should be "variable", and interpret the empty echo later, but that would need a better simulator
                return value

        if value == "^":
            return value
        return value.rstrip("^")

    def interpret_set(self, cmd):
        state = "init"
        option = None
        var_name = ""
        var_value = ""
        quote = None
        old_state = None
        stop_parsing = len(cmd)

        for idx, char in enumerate(cmd):
            # print(f"{idx}. C: {char} S: {state}, {var_value}")
            if idx >= stop_parsing:
                break
            if state == "init":
                if char == " ":
                    continue
                elif char == "/":
                    state = "option"
                elif char == '"':
                    quote = '"'
                    stop_parsing = cmd.rfind('"')
                    if idx == stop_parsing:
                        stop_parsing = len(cmd)
                    state = "var"
                elif char == "^":
                    old_state = state
                    state = "escape"
                else:
                    state = "var"
                    var_name += char
            elif state == "option":
                option = char.lower()
                state = "init"
            elif state == "var":
                if char == "=":
                    state = "value"
                elif not quote and char == '"':
                    quote = '"'
                    var_name += char
                elif char == "^":
                    old_state = state
                    state = "escape"
                else:
                    var_name += char
            elif state == "value":
                if char == "^":
                    old_state = state
                    state = "escape"
                else:
                    var_value += char
            elif state == "escape":
                if old_state == "init":
                    if char == '"':
                        quote = '^"'
                        stop_parsing = cmd.rfind('"')
                        if idx == stop_parsing:
                            stop_parsing = len(cmd)
                        state = "init"
                        old_state = None
                    else:
                        state = "var"
                        var_name += char
                        old_state = None
                elif old_state == "var":
                    if quote == '"' and char in QUOTED_CHARS:
                        var_name += "^"
                    if not quote and char == '"':
                        quote = '^"'
                    var_name += char
                    state = old_state
                    old_state = None
                elif old_state == "value":
                    var_value += char
                    state = old_state
                    old_state = None

        if option == "a":
            var_name = var_name.strip(" ")
            for char in QUOTED_CHARS:
                var_name = var_name.replace(char, "")
            var_value = f"({var_value.strip(' ')})"
        elif option == "p":
            var_value = "__input__"

        var_name = var_name.lstrip(" ")
        if not quote:
            var_name = var_name.lstrip('^"').replace('^"', '"')

        return (var_name, var_value)

    def interpret_curl(self, cmd):
        # Batch specific obfuscation that is not handled before for echo/variable purposes, can be stripped here
        cmd = cmd.replace('""', "")
        split_cmd = shlex.split(cmd, posix=False)
        args, unknown = self.curl_parser.parse_known_args(split_cmd[1:])

        dst = args.output
        if args.remote_name:
            dst = os.path.basename(urlparse(args.url).path)

        self.traits["download"].append((cmd, {"src": args.url, "dst": dst}))

    def interpret_powershell(self, normalized_comm):
        try:
            ori_cmd = shlex.split(normalized_comm)
            cmd = shlex.split(normalized_comm.lower())
        except ValueError:
            return

        ps1_cmd = None
        for idx, part in enumerate(cmd):
            if re.match(ENC_RE, part.encode()):
                ps1_cmd = base64.b64decode(ori_cmd[idx + 1]).replace(b"\x00", b"")
                break
            elif re.match(PWR_CMD_RE, part.encode()):
                ps1_cmd = ori_cmd[idx + 1].encode()
                break
        if ps1_cmd is None:
            ps1_cmd = ori_cmd[-1].encode()

        if ps1_cmd:
            self.exec_ps1.append(ps1_cmd.strip(b'"'))

    def interpret_command(self, normalized_comm):
        if normalized_comm[:3].lower() == "rem":
            return

        # We need to keep the last space in case the command is "set EXP=43 " so that the value will be "43 "
        # normalized_comm = normalized_comm.strip()

        # remove paranthesis
        index = 0
        last = len(normalized_comm) - 1
        while index < last and (normalized_comm[index] == " " or normalized_comm[index] == "("):
            if normalized_comm[index] == "(":
                while last > index and (normalized_comm[last] == " " or normalized_comm[last] == ")"):
                    if normalized_comm[last] == ")":
                        last -= 1
                        break
                    last -= 1
            index += 1
        normalized_comm = normalized_comm[index : last + 1]

        if not normalized_comm:
            return

        if normalized_comm[0] == "@":
            normalized_comm = normalized_comm[1:]

        normalized_comm_lower = normalized_comm.lower()
        if normalized_comm_lower.startswith("call"):
            # TODO: Not a perfect interpretation as the @ sign of the recursive command shouldn't be remove
            # This shouldn't work:
            # call @set EXP=43
            # But this should:
            # call set EXP=43
            self.interpret_command(normalized_comm[5:])
            return

        if normalized_comm_lower.startswith("start"):
            start_re = (
                r"start(.exe)?"
                r"(\/min|\/max|\/wait|\/low|\/normal|\/abovenormal|\/belownormal|\/high|\/realtime|\/b|\/i|\/w|\s+)*"
                # TODO: Add Node + Affinity options
                # TODO: Add title + path keys
                r"(?P<cmd>.*)"
            )
            match = re.match(start_re, normalized_comm, re.IGNORECASE)
            if match is not None and match.group("cmd") is not None:
                self.interpret_command(match.group("cmd"))
            return

        if normalized_comm_lower.startswith("cmd"):
            cmd_command = r"cmd(.exe)?\s*((\/A|\/U|\/Q|\/D)\s+|((\/E|\/F|\/V):(ON|OFF))\s*)*(\/c|\/r)\s*(?P<cmd>.*)"
            match = re.search(cmd_command, normalized_comm, re.IGNORECASE)
            if match is not None and match.group("cmd") is not None:
                self.exec_cmd.append(match.group("cmd").strip('"'))
            return

        if normalized_comm_lower.startswith("setlocal"):
            # Just so we don't go into the set command
            return

        if normalized_comm_lower.startswith("set"):
            # interpreting set command
            var_name, var_value = self.interpret_set(normalized_comm[3:])
            if var_value == "":
                if var_name.lower() in self.variables:
                    del self.variables[var_name.lower()]
            else:
                self.variables[var_name.lower()] = var_value
            return

        if normalized_comm_lower.startswith("curl"):
            self.interpret_curl(normalized_comm)

        if normalized_comm_lower.startswith("powershell"):
            self.interpret_powershell(normalized_comm)

    # pushdown automata
    def normalize_command(self, command):
        if command[:3].lower() == "rem":
            return command

        state = "init"
        normalized_com = ""
        stack = []
        traits = {"start_with_var": False, "var_used": 0}
        for char in command:
            # print(f"C:{char} S:{state} N:{normalized_com}")
            if state == "init":  # init state
                if char == '"':  # quote is on
                    state = "str_s"
                    if normalized_com and normalized_com[-1] == '"':
                        normalized_com = normalized_com[:-1]
                    else:
                        normalized_com += char
                elif char == "," or char == ";":  # or char == "\t": EDIT: How about we keep those tabs?
                    # commas (",") are replaced by spaces, unless they are part of a string in doublequotes
                    # semicolons (";") are replaced by spaces, unless they are part of a string in doublequotes
                    # tabs are replaced by a single space
                    # http://www.robvanderwoude.com/parameters.php
                    normalized_com += " "
                elif char == "^":  # next character must be escaped
                    stack.append(state)
                    state = "escape"
                elif char == "%":  # variable start
                    variable_start = len(normalized_com)
                    normalized_com += char
                    stack.append(state)
                    state = "var_s"
                elif char == "!":
                    variable_start = len(normalized_com)
                    normalized_com += char
                    stack.append(state)
                    state = "var_s_2"
                else:
                    normalized_com += char
            elif state == "str_s":
                if char == '"':
                    state = "init"
                    normalized_com += char
                elif char == "%":
                    variable_start = len(normalized_com)
                    normalized_com += char
                    stack.append("str_s")
                    state = "var_s"  # seen %
                elif char == "!":
                    variable_start = len(normalized_com)
                    normalized_com += char
                    stack.append("str_s")
                    state = "var_s_2"  # seen !
                elif char == "^":
                    state = "escape"
                    stack.append("str_s")
                else:
                    normalized_com += char
            elif state == "var_s":
                if char == "%" and normalized_com[-1] != char:
                    normalized_com += char
                    value = self.get_value(normalized_com[variable_start:])
                    normalized_com = normalized_com[:variable_start]
                    if len(normalized_com) == 0:
                        traits["start_with_var"] = True
                    normalized_com += self.normalize_command(value)
                    traits["var_used"] += 1
                    state = stack.pop()
                elif char == "%":  # Two % in a row
                    normalized_com += char
                    state = stack.pop()
                elif char == "^":
                    # Do not escape in vars?
                    # state = "escape"
                    # stack.append("var_s")
                    normalized_com += char
                elif char == "*" and len(normalized_com) == variable_start + 1:
                    # Assume no parameter were passed
                    normalized_com = normalized_com[:variable_start]
                    state = stack.pop()
                elif char.isdigit() and normalized_com[variable_start:] in [
                    "%",
                    "%~",
                    "%~f",
                    "%~d",
                    "%~p",
                    "%~n",
                    "%~x",
                    "%~s",
                    "%~a",
                    "%~t",
                    "%~z",
                ]:
                    # https://www.programming-books.io/essential/batch/-percent-tilde-f4263820c2db41e399c77259970464f1.html
                    # TODO: Better handling of letter combination (i.e. %~xsa0)
                    # Could also return different values of script.bat if we want to parse the options
                    normalized_com += char
                    if char == "0":
                        value = "script.bat"
                    else:
                        value = ""  # Assume no parameter were passed
                    normalized_com = normalized_com[:variable_start]
                    normalized_com += value
                    state = stack.pop()
                else:
                    normalized_com += char
            elif state == "var_s_2":
                if char == "!" and normalized_com[-1] != char:
                    normalized_com += char
                    value = self.get_value(normalized_com[variable_start:])
                    normalized_com = normalized_com[:variable_start]
                    if len(normalized_com) == 0:
                        traits["start_with_var"] = True
                    normalized_com += self.normalize_command(value)
                    traits["var_used"] += 1
                    state = stack.pop()
                elif char == "!":
                    normalized_com += char
                elif char == "^":
                    state = "escape"
                    stack.append("var_s_2")
                else:
                    normalized_com += char
            elif state == "escape":
                if char in QUOTED_CHARS:
                    normalized_com += "^"
                normalized_com += char
                state = stack.pop()
                if char == "%":
                    if state == "var_s":
                        value = self.get_value(normalized_com[variable_start:])
                        normalized_com = normalized_com[:variable_start]
                        if len(normalized_com) == 0:
                            traits["start_with_var"] = True
                        normalized_com += self.normalize_command(value)
                        traits["var_used"] += 1
                        state = stack.pop()
                    else:
                        variable_start = len(normalized_com) - 1
                        stack.append(state)
                        state = "var_s"
                elif char == "!":
                    if state == "var_s_2":
                        value = self.get_value(normalized_com[variable_start:])
                        normalized_com = normalized_com[:variable_start]
                        if len(normalized_com) == 0:
                            traits["start_with_var"] = True
                        normalized_com += self.normalize_command(value)
                        traits["var_used"] += 1
                        state = stack.pop()
                    else:
                        variable_start = len(normalized_com) - 1
                        stack.append(state)
                        state = "var_s_2"

        if state in ["var_s", "var_s_2"]:
            normalized_com = normalized_com[:variable_start] + normalized_com[variable_start + 1 :]
        if state == "escape":
            normalized_com += "^"

        if traits["start_with_var"]:
            self.traits["start_with_var"].append((command, normalized_com))
        self.traits["var_used"].append((command, normalized_com, traits["var_used"]))

        return normalized_com

    def analyze_logical_line(self, logical_line, working_directory, f, extracted_files):
        commands = self.get_commands(logical_line)
        for command in commands:
            normalized_comm = self.normalize_command(command)
            if len(list(self.get_commands(normalized_comm))) > 1:
                self.traits["command-grouping"].append({"Command": command, "Normalized": normalized_comm})
                self.analyze_logical_line(normalized_comm, working_directory, f, extracted_files)
            else:
                self.interpret_command(normalized_comm)
                f.write(normalized_comm)
                f.write("\n")
                for lolbas in RARE_LOLBAS:
                    if lolbas in normalized_comm:
                        self.traits["LOLBAS"].append({"LOLBAS": lolbas, "Command": normalized_comm})
                if len(self.exec_cmd) > 0:
                    for child_cmd in self.exec_cmd:
                        child_deobfuscator = copy.deepcopy(self)
                        child_deobfuscator.exec_cmd.clear()
                        child_fd, child_path = tempfile.mkstemp(suffix=".bat", prefix="child_", dir=working_directory)
                        with open(child_path, "w") as child_f:
                            child_deobfuscator.analyze_logical_line(
                                child_cmd, working_directory, child_f, extracted_files
                            )
                        with open(child_path, "rb") as cmd_f:
                            sha256hash = hashlib.sha256(cmd_f.read()).hexdigest()
                        bat_filename = f"{sha256hash[0:10]}.bat"
                        shutil.move(child_path, os.path.join(working_directory, bat_filename))
                        extracted_files["batch"].append((bat_filename, sha256hash))
                    self.exec_cmd.clear()
                if len(self.exec_ps1) > 0:
                    for child_ps1 in self.exec_ps1:
                        sha256hash = hashlib.sha256(child_ps1).hexdigest()
                        if any(
                            extracted_file_hash == sha256hash
                            for _, extracted_file_hash in extracted_files.get("powershell", [])
                        ):
                            continue
                        powershell_filename = f"{sha256hash[0:10]}.ps1"
                        powershell_file_path = os.path.join(working_directory, powershell_filename)
                        with open(powershell_file_path, "wb") as ps1_f:
                            ps1_f.write(child_ps1)
                        extracted_files["powershell"].append((powershell_filename, sha256hash))
                    self.exec_ps1.clear()

    def analyze(self, file_path, working_directory):
        extracted_files = defaultdict(list)

        file_name = "deobfuscated_bat.bat"
        temp_path = os.path.join(working_directory, file_name)
        with open(temp_path, "w") as f:
            for logical_line in self.read_logical_line(file_path):
                self.analyze_logical_line(logical_line, working_directory, f, extracted_files)

        # Figure out if we're dealing with a Complex One-Liner
        # Ignore empty lines to determine if it is a One-Liner
        self.traits["one-liner"] = False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            firstline = False
            for line in f:
                if line.strip():
                    if not firstline:
                        self.traits["one-liner"] = True
                        firstline = True
                    else:
                        self.traits["one-liner"] = False
                        break

        with open(temp_path, "rb") as f:
            deobfuscated_data = f.read()
            if self.traits["one-liner"]:
                resulting_line_count = deobfuscated_data.count(b"\n")
                if resulting_line_count >= self.complex_one_liner_threshold:
                    self.traits["complex-one-liner"] = resulting_line_count
            sha256hash = hashlib.sha256(deobfuscated_data).hexdigest()
            bat_filename = f"{sha256hash[0:10]}_deobfuscated.bat"
            shutil.move(temp_path, os.path.join(working_directory, bat_filename))

        return bat_filename, extracted_files


def interpret_logical_line(deobfuscator, logical_line, tab=""):
    commands = deobfuscator.get_commands(logical_line)
    for command in commands:
        normalized_comm = deobfuscator.normalize_command(command)
        deobfuscator.interpret_command(normalized_comm)
        print(tab + normalized_comm)
        if len(deobfuscator.exec_cmd) > 0:
            print(tab + "[CHILD CMD]")
            for child_cmd in deobfuscator.exec_cmd:
                child_deobfuscator = copy.deepcopy(deobfuscator)
                child_deobfuscator.exec_cmd.clear()
                interpret_logical_line(child_deobfuscator, child_cmd, tab=tab + "\t")
            deobfuscator.exec_cmd.clear()
            print(tab + "[END OF CHILD CMD]")


def interpret_logical_line_str(deobfuscator, logical_line, tab=""):
    str = ""
    commands = deobfuscator.get_commands(logical_line)
    for command in commands:
        normalized_comm = deobfuscator.normalize_command(command)
        deobfuscator.interpret_command(normalized_comm)
        str = str + tab + normalized_comm
        if len(deobfuscator.exec_cmd) > 0:
            str = str + tab + "[CHILD CMD]"
            for child_cmd in deobfuscator.exec_cmd:
                child_deobfuscator = copy.deepcopy(deobfuscator)
                child_deobfuscator.exec_cmd.clear()
                interpret_logical_line(child_deobfuscator, child_cmd, tab=tab + "\t")
            deobfuscator.exec_cmd.clear()
            str = str + tab + "[END OF CHILD CMD]"
    return str


def handle_bat_file(deobfuscator, fpath):
    strs = []
    if os.path.isfile(fpath):
        try:
            for logical_line in deobfuscator.read_logical_line(fpath):
                try:
                    strs.append(interpret_logical_line_str(deobfuscator, logical_line))
                except Exception as e:
                    print(e)
                    pass
        except Exception as e:
            print(e)
            pass
    if strs:
        return "\r\n".join(strs)
    else:
        return ""


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
