import pytest

from batch_deobfuscator.batch_interpreter import BatchDeobfuscator


class TestUnittests:
    @staticmethod
    def test_simple_set():
        deobfuscator = BatchDeobfuscator()
        deobfuscator.interpret_command("set WALLET=43DTEF92be6XcPj5Z7U")
        res = deobfuscator.normalize_command("echo %WALLET%")
        assert res == "echo 43DTEF92be6XcPj5Z7U"

    @staticmethod
    def test_variable_in_for():
        deobfuscator = BatchDeobfuscator()
        deobfuscator.interpret_command("set WALLET=43DTEF92be6XcPj5Z7U")
        cmd = 'for /f "delims=." %%a in ("%WALLET%") do set WALLET_BASE=%%a'
        res = deobfuscator.normalize_command(cmd)
        assert res == 'for /f "delims=." %%a in ("43DTEF92be6XcPj5Z7U") do set WALLET_BASE=%%a'

    @staticmethod
    def test_unset_variable():
        deobfuscator = BatchDeobfuscator()
        cmd = "echo ERROR: Wrong wallet address length (should be 106 or 95): %WALLET_BASE_LEN%"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo ERROR: Wrong wallet address length (should be 106 or 95): "

    @staticmethod
    def test_caret_pipe():
        deobfuscator = BatchDeobfuscator()
        cmd1 = 'echo tasklist /fi "imagename eq jin.exe" ^| find ":" ^>NUL\n'
        cmd2 = [x for x in deobfuscator.get_commands(cmd1)]
        assert cmd2 == ['echo tasklist /fi "imagename eq jin.exe" ^| find ":" ^>NUL']
        cmd3 = deobfuscator.normalize_command(cmd2[0])
        assert cmd3 == 'echo tasklist /fi "imagename eq jin.exe" ^| find ":" ^>NUL'
        cmd4 = [x for x in deobfuscator.get_commands(cmd3)]
        assert cmd4 == ['echo tasklist /fi "imagename eq jin.exe" ^| find ":" ^>NUL']

    @staticmethod
    def test_simple_set_a():
        deobfuscator = BatchDeobfuscator()
        res = deobfuscator.normalize_command("echo %NUMBER_OF_PROCESSORS%")
        assert res == "echo 4"

        cmd = 'set /a "EXP_MONERO_HASHRATE = %NUMBER_OF_PROCESSORS% * 700 / 1000"'
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)
        cmd3 = deobfuscator.normalize_command("echo %EXP_MONERO_HASHRATE%")
        assert cmd3 == "echo (4 * 700 / 1000)"

    @staticmethod
    @pytest.mark.parametrize(
        "var, echo, result",
        [
            # Simple
            # No space
            ("set EXP=43", "echo *%EXP%*", "echo *43*"),
            ("set EXP=43", "echo *%EXP %*", "echo **"),
            ("set EXP=43", "echo *% EXP%*", "echo **"),
            ("set EXP=43", "echo *% EXP %*", "echo **"),
            # Space after var
            ("set EXP =43", "echo *%EXP%*", "echo **"),
            ("set EXP =43", "echo *%EXP %*", "echo *43*"),
            ("set EXP =43", "echo *% EXP%*", "echo **"),
            ("set EXP =43", "echo *% EXP %*", "echo **"),
            # Space after equal
            ("set EXP= 43", "echo *%EXP%*", "echo * 43*"),
            ("set EXP= 43", "echo *%EXP %*", "echo **"),
            ("set EXP= 43", "echo *% EXP%*", "echo **"),
            ("set EXP= 43", "echo *% EXP %*", "echo **"),
            # Space after value
            ("set EXP=43 ", "echo *%EXP%*", "echo *43 *"),
            ("set EXP=43 ", "echo *%EXP %*", "echo **"),
            ("set EXP=43 ", "echo *% EXP%*", "echo **"),
            ("set EXP=43 ", "echo *% EXP %*", "echo **"),
            # Space after var and after equal
            ("set EXP = 43", "echo *%EXP%*", "echo **"),
            ("set EXP = 43", "echo *%EXP %*", "echo * 43*"),
            ("set EXP = 43", "echo *% EXP%*", "echo **"),
            ("set EXP = 43", "echo *% EXP %*", "echo **"),
            # Double quote
            # Single quote for both var and value
            ("set \"'EXP=43'\"", "echo *%EXP%*", "echo **"),
            ("set \"'EXP=43'\"", "echo *%EXP %*", "echo **"),
            ("set \"'EXP=43'\"", "echo *% EXP%*", "echo **"),
            ("set \"'EXP=43'\"", "echo *% EXP %*", "echo **"),
            ("set \"'EXP=43'\"", "echo *%'EXP%*", "echo *43'*"),
            # Space after var
            ('set "EXP =43"', "echo *%EXP%*", "echo **"),
            ('set "EXP =43"', "echo *%EXP %*", "echo *43*"),
            ('set "EXP =43"', "echo *% EXP%*", "echo **"),
            ('set "EXP =43"', "echo *% EXP %*", "echo **"),
            # Space after equal
            ('set "EXP= 43"', "echo *%EXP%*", "echo * 43*"),
            ('set "EXP= 43"', "echo *%EXP %*", "echo **"),
            ('set "EXP= 43"', "echo *% EXP%*", "echo **"),
            ('set "EXP= 43"', "echo *% EXP %*", "echo **"),
            # Space after var and after equal
            ('set "EXP = 43"', "echo *%EXP%*", "echo **"),
            ('set "EXP = 43"', "echo *%EXP %*", "echo * 43*"),
            ('set "EXP = 43"', "echo *% EXP%*", "echo **"),
            ('set "EXP = 43"', "echo *% EXP %*", "echo **"),
            # Space before var, after var, after equal and after value
            ('set " EXP = 43 "', "echo *%EXP%*", "echo **"),
            ('set " EXP = 43 "', "echo *%EXP %*", "echo * 43 *"),
            ('set " EXP = 43 "', "echo *% EXP%*", "echo **"),
            ('set " EXP = 43 "', "echo *% EXP %*", "echo **"),
            # Single quote
            ("set \"EXP='43'\"", "echo *%EXP%*", "echo *'43'*"),
            ("set \"EXP=' 43'\"", "echo *%EXP%*", "echo *' 43'*"),
            ("set \"EXP =' 43'\"", "echo *%EXP %*", "echo *' 43'*"),
            ("set \"EXP = ' 43'\"", "echo *%EXP %*", "echo * ' 43'*"),
            ("set 'EXP=\"43\"'", "echo *%'EXP%*", 'echo *"43"\'*'),
            ("set \" EXP '=43 ' \" ", "echo *%EXP '%*", "echo *43 ' *"),
            # Double quote as value
            ('set EXP =43^"', "echo *%EXP %*", 'echo *43"*'),
            ('set EXP =43^"3', "echo *%EXP %*", 'echo *43"3*'),
            ('set "EXP=43^""', "echo *%EXP%*", 'echo *43"*'),
            ('set "EXP=43^"3"', "echo *%EXP%*", 'echo *43"3*'),
            ('set EXP=43^"^|', "echo *%EXP%*", 'echo *43"|*'),
            # Getting into really weird stuff
            ("set EXP=4=3", "echo *%EXP%*", "echo *4=3*"),
            ('set ""EXP=43"', 'echo *%"EXP%*', "echo *43*"),
            ('set ""EXP=4"3', 'echo *%"EXP%*', "echo *4*"),
            ('set """EXP=43"', "echo *%EXP%*", "echo **"),
            ('set """EXP=43"', 'echo *%""EXP%*', "echo *43*"),
            ('set "E^XP=43"', "echo *%EXP%*", "echo *43*"),
            ('set " ^"EXP=43"', 'echo *%^"EXP%*', "echo *43*"),
            ('set ^"EXP=43', "echo *%EXP%*", "echo *43*"),
            ('set E^"XP=43', 'echo *%E"XP%*', "echo *43*"),
            ('set E"XP=4"3', 'echo *%E"XP%*', 'echo *4"3*'),
            ('set E"XP=4^""3', 'echo *%E"XP%*', 'echo *4""3*'),
            ('set EXP^"=43', 'echo *%EXP"%*', "echo *43*"),
            ("set EXP=43^^", "echo *%EXP%*", "echo *43*"),
            ("set EXP=4^^3", "echo *%EXP%*", "echo *43*"),
            ("set EXP=43^^ ", "echo *%EXP%*", "echo *43 *"),
            ("set E^^XP=43", "echo *%E^XP%*", "echo *43*"),
            ('set ^"E^^XP=43"', "echo *%E^XP%*", "echo *43*"),
            ('set ^"E^^XP=43^"', "echo *%E^XP%*", "echo *43*"),
            ('set ^"E^^XP=43', "echo *%E^XP%*", "echo *43*"),
            ('set "E^^XP=43"', "echo *%E^^XP%*", "echo *43*"),
            ('set "E^^XP=43', "echo *%E^^XP%*", "echo *43*"),
            ('set E^"XP=4^"3', 'echo *%E"XP%*', 'echo *4"3*'),
            ('set ^"EXP=4^"3', "echo *%EXP%*", "echo *4*"),
            ('set ^"EXP= 4^"3', "echo *%EXP%*", "echo * 4*"),
            ('set ^"E^"XP=43"', 'echo *%E"XP%*', "echo *43*"),
            ('set ^"E^"XP=4^"3', 'echo *%E"XP%*', "echo *4*"),
            ('set ^"E"XP=4^"3"', 'echo *%E"XP%*', 'echo *4"3*'),
            ('set ^"E"XP=4^"3""', 'echo *%E"XP%*', 'echo *4"3"*'),
            ('set "E"XP=4^"3""', 'echo *%E"XP%*', 'echo *4"3"*'),
            ('set ^"E""XP=4^"3', 'echo *%E""XP%*', "echo *4*"),
            ('set "E^"XP=43"', 'echo *%E^"XP%*', "echo *43*"),
            ('set "E^"X"P=43"', 'echo *%E^"X"P%*', "echo *43*"),
            ('set E"E^"XP=43"', 'echo *%E"E^"XP%*', 'echo *43"*'),
            ('set E"E^"XP=43', 'echo *%E"E^"XP%*', "echo *43*"),
            ('set E^"E"X"P=43"', 'echo *%E"E"X"P%*', 'echo *43"*'),
            ('set E"E^"X"P=43"', 'echo *%E"E^"X"P%*', 'echo *43"*'),
            ("set ^|EXP=43", "echo *%|EXP%*", "echo *43*"),
            # TODO: Really, how should we handle that?
            # 'set ""EXP=43'
            # 'set'
            # 'set E'
            # 'set EXP'
            # 'set ^"E^"XP=43'
            # 'set ^"E""XP=43'
            #
            # option a
            ('set /a "EXP = 4 * 700 / 1000"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ('set /A "EXP = 4 * 700 / 1000"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ('SET /A "EXP = 4 * 700 / 1000"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ('SET /a "EXP = 4 * 700 / 1000"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ("set /a EXP = 4 * 700 / 1000", "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ('set /a ^"EXP = 4 * 700 / 1000"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ('set /a ^"E^"XP = 4 * 700 / 1000^"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ('set /a "EXP^" = 4 * 700 / 1000"', "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ("set /a EX^^P = 4 * 700 / 1000", "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ("set /a EX^P = 4 * 700 / 1000", "echo *%EXP%*", "echo *(4 * 700 / 1000)*"),
            ("set /a EXP = 4 * OTHER", "echo *%EXP%*", "echo *(4 * OTHER)*"),
            ("set/a EXP = 4 * 2", "echo *%EXP%*", "echo *(4 * 2)*"),
            ("set/AEXP=43", "echo *%EXP%*", "echo *(43)*"),
            ("set/AEXP=4 * 3", "echo *%EXP%*", "echo *(4 * 3)*"),
            # TODO: Really, how should we handle that?
            # 'set /a "EX|P = 4 * 700 / 1000'
            # "set /a EX|P = 4 * 700 / 1000"
            # "set /a EX^|P = 4 * 700 / 1000"
            #
            # option p
            ('set /p "EXP"="What is"', 'echo *%EXP"%*', "echo *__input__*"),
            ('set /p EXP="What is', "echo *%EXP%*", "echo *__input__*"),
            ("set /p EXP=What is", "echo *%EXP%*", "echo *__input__*"),
            ("SET /p EXP=What is", "echo *%EXP%*", "echo *__input__*"),
            ("SET /P EXP=What is", "echo *%EXP%*", "echo *__input__*"),
            ("set /P EXP=What is", "echo *%EXP%*", "echo *__input__*"),
            ('set /p EXP "=What is', 'echo *%EXP "%*', "echo *__input__*"),
            ('set /p  EXP "=What is', 'echo *%EXP "%*', "echo *__input__*"),
            ('set /p "EXP =What is', "echo *%EXP %*", "echo *__input__*"),
            ('set /p "EXP ="What is"', "echo *%EXP %*", "echo *__input__*"),
            ('set /p E"XP =What is', 'echo *%E"XP %*', "echo *__input__*"),
            ('set /p E^"XP ="What is"', 'echo *%E"XP %*', "echo *__input__*"),
            ('set /p "E^"XP ="What is"', 'echo *%E^"XP %*', "echo *__input__*"),
            ('set /p E^"XP =What is', 'echo *%E"XP %*', "echo *__input__*"),
            ('set /p "E^|XP =What is', "echo *%E^|XP %*", "echo *__input__*"),
            ("set /p E^|XP =What is", "echo *%E|XP %*", "echo *__input__*"),
            ('set /p ^"EXP =What is', "echo *%EXP %*", "echo *__input__*"),
            ("set /p ^|EXP =What is", "echo *%|EXP %*", "echo *__input__*"),
            # TODO: Really, how should we handle that?
            # 'set /p "EXP "=What is'
            # 'set /p "E^"XP =What is'
            # What about some weird echo statement now?
            ("set EXP=43", "echo %EXP%", "echo 43"),
            ("set EXP=43", "echo !EXP!", "echo 43"),
            ("set EXP=43", "echo ^%EXP%", "echo 43"),
            ("set EXP=43", "echo ^!EXP!", "echo 43"),
            # ("set EXP=43", "echo ^%EX^P%", "echo 43"),  # That's wrong... it actually prints the next line. Ignoring.
            ("set EXP=43", "echo ^!EX^P!", "echo 43"),
            # ("set EXP=43", "echo ^%EXP^%", "echo 43"),  # That's wrong... it actually prints the next line. Ignoring.
            ("set EXP=43", "echo ^!EXP^!", "echo 43"),
        ],
    )
    def test_set_command(var, echo, result):
        deobfuscator = BatchDeobfuscator()
        deobfuscator.interpret_command(var)
        res = deobfuscator.normalize_command(echo)
        assert res == result

    @staticmethod
    def test_clear_variable_with_set():
        # If you specify only a variable and an equal sign (without <string>) for the set command,
        # the <string> value associated with the variable is cleared (as if the variable is not there).
        deobfuscator = BatchDeobfuscator()
        assert "exp" not in deobfuscator.variables
        res = deobfuscator.normalize_command("echo *%EXP%*")
        assert res == "echo **"
        deobfuscator.interpret_command("set EXP=43")
        assert "exp" in deobfuscator.variables
        res = deobfuscator.normalize_command("echo *%EXP%*")
        assert res == "echo *43*"
        deobfuscator.interpret_command("set EXP= ")
        assert "exp" in deobfuscator.variables
        res = deobfuscator.normalize_command("echo *%EXP%*")
        assert res == "echo * *"
        deobfuscator.interpret_command("set EXP=")
        assert "exp" not in deobfuscator.variables
        res = deobfuscator.normalize_command("echo *%EXP%*")
        assert res == "echo **"

    @staticmethod
    @pytest.mark.skip()
    def test_beautify_strlen_function():
        # Figure out if it translate somewhat correctly, and how to make it more readable after processing
        # Taken from 6c46550db4dcb3f5171c69c5f1723362f99ec0f16f6d7ab61b6f8d169a6e6bc8
        """
        ":strlen string len"
        "setlocal EnableDelayedExpansion"
        'set "token=#%~1" & set "len=0"'
        "for /L %%A in (12,-1,0) do ("
        '  set/A "len|=1<<%%A"'
        '  for %%B in (!len!) do if "!token:~%%B,1!"=="" set/A "len&=~1<<%%A"'
        ")"
        """

    @staticmethod
    @pytest.mark.parametrize(
        "statement, commands",
        [
            ('IF "A"=="A" echo AAA', ['IF "A"=="A" (', "echo AAA", ")"]),
            ('IF "A"=="A" (echo AAA)', ['IF "A"=="A" (', "echo AAA", ")"]),
            ('IF "A"=="A" (echo AAA) ELSE echo BBB', ['IF "A"=="A" (', "echo AAA", ") ELSE (", "echo BBB", ")"]),
            (
                'echo ABC && IF "A"=="A" (echo AAA) ELSE echo BBB',
                ["echo ABC", 'IF "A"=="A" (', "echo AAA", ") ELSE (", "echo BBB", ")"],
            ),
            (
                'echo ABC && IF "A"=="A" (echo AAA) ELSE (echo BBB)',
                ["echo ABC", 'IF "A"=="A" (', "echo AAA", ") ELSE (", "echo BBB", ")"],
            ),
            (
                'IF EXIST "%USERPROFILE%\\jin" GOTO REMOVE_DIR1',
                ['IF EXIST "%USERPROFILE%\\jin" (', "GOTO REMOVE_DIR1", ")"],
            ),
            (
                "IF defined EXP (echo Defined) ELSE (echo Undef)",
                ["IF defined EXP (", "echo Defined", ") ELSE (", "echo Undef", ")"],
            ),
            (
                "if %EXP% gtr 8192 ( set PORT=18192 & goto PORT_OK )",
                ["if %EXP% gtr 8192 (", " set PORT=18192", "goto PORT_OK )"],
            ),
            ("if %EXP% gtr 8192 (", ["if %EXP% gtr 8192 ("]),
            (
                "if %errorLevel% == 0 (set ADMIN=1) else (set ADMIN=0)",
                ["if %errorLevel% == 0 (", "set ADMIN=1", ") else (", "set ADMIN=0", ")"],
            ),
            (
                'if exist "%USERPROFILE%\\Start Menu\\Programs" (echo AAA)',
                ['if exist "%USERPROFILE%\\Start Menu\\Programs" (', "echo AAA", ")"],
            ),
            (
                'if exist "%USERPROFILE%\\Start Menu\\Programs" echo AAA',
                ['if exist "%USERPROFILE%\\Start Menu\\Programs" (', "echo AAA", ")"],
            ),
            (
                "if [%var%]==[value] echo AAA",
                ["if [%var%]==[value] (", "echo AAA", ")"],
            ),
            (
                'if "%var%"==[value] echo AAA',
                ['if "%var%"==[value] (', "echo AAA", ")"],
            ),
        ],
    )
    def test_if_statements(statement, commands):
        deobfuscator = BatchDeobfuscator()
        assert [x for x in deobfuscator.get_commands(statement)] == commands

    @staticmethod
    def test_single_quote_var_name_rewrite_1():
        deobfuscator = BatchDeobfuscator()

        cmd = "%os:~-4,1%%comspec:~-1,1%%comspec:~14,1%%commonprogramfiles:~-6,1%'=^^^1^^^\\^^^)%comspec:~-13,1%u^^^,^^^%pathext:~31,1%b^^^8%commonprogramfiles:~9,1%^^^^^^^/v^^^&^^^U%os:~-9,1%^^^%pathext:~6,1%k%programfiles:~-12,1%p^^^[^^^*^^^@^^^~%programfiles:~-8,1%^^^%pathext:~11,1%q%comspec:~-14,1%^^^%commonprogramfiles:~24,1%^^^R^^^%pathext:~12,1%^^^0f^^^I^^^%comspec:~-9,1%^^^{^^^$%comspec:~-7,1%^^^K%programfiles:~-2,1%^^^7^^^9z%commonprogramfiles:~-11,1%^^^G^^^%os:~9,1%^^^L^^^=^^^(%commonprogramfiles:~-16,1%^^^%commonprogramfiles:~-12,1%h%comspec:~-15,1%^^^6^^^%commonprogramfiles:~10,1%^^^\"^^^Q^^^_^^^%pathext:~2,1%j^^^`%commonprogramfiles:~6,1%^^^Y^^^]^^^+^^^%pathext:~18,1%^^^-^^^%pathext:~26,1%^^^|^^^%comspec:~17,1%^^^%pathext:~7,1%^^^<%commonprogramfiles:~22,1%^^^%pathext:~17,1%^^^;^^^%os:~-10,1%^^^%os:~8,1%^^^%pathext:~41,1%^^^>^^^}^^^#^^^'%os:~-7,1%^^^.^^^5%os:~5,1%^^^4^^^:^^^%programfiles:~3,1%^^^%pathext:~47,1%%comspec:~25,1%^^^?^^^Z"  # noqa: E501
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)
        assert deobfuscator.variables["'"].startswith("^1^\\^)tu^")

        cmd = "%':~43,1%%':~-96,1%%':~6,1%"
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "set"

        cmd = "echo AAA%':~-138,1%%':~43,1%%':~-96,1%%':~6,1%%':~89,1%%':~-20,1%%':~-82,1%abbbc%':~-138,1%set mj=kx"
        cmd2 = deobfuscator.normalize_command(cmd)
        for cmd in deobfuscator.get_commands(cmd2):
            cmd2 = deobfuscator.normalize_command(cmd)
            deobfuscator.interpret_command(cmd2)
        assert deobfuscator.variables["'"] == "abbbc"

    @staticmethod
    def test_args():
        deobfuscator = BatchDeobfuscator()

        cmd = "echo %0"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo script.bat"

        cmd = "echo %1"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo "

        cmd = "echo %3c%3%A"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo cA"

        cmd = "echo %3c%3%A%"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo c"

        cmd = "set A=123"
        deobfuscator.interpret_command(cmd)

        cmd = "echo %3c%3%A%"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo c123"

        cmd = "echo %0%A%"
        res = deobfuscator.normalize_command(cmd)
        assert res == "echo script.bat123"

    @staticmethod
    def test_single_quote_var_name_rewrite_2():
        # Taken from 8d20c8a8104f29e7ec2ff158103fa73d3e9d357b646e2ff0487b880ab6462643
        deobfuscator = BatchDeobfuscator()

        cmd = "%os:~-4,1%%comspec:~-1,1%%comspec:~14,1%%commonprogramfiles:~-6,1%'=^^^1^^^\\^^^)%comspec:~-13,1%u^^^,^^^%pathext:~31,1%b^^^8%commonprogramfiles:~9,1%^^^^^^^/v^^^&^^^U%os:~-9,1%^^^%pathext:~6,1%k%programfiles:~-12,1%p^^^[^^^*^^^@^^^~%programfiles:~-8,1%^^^%pathext:~11,1%q%comspec:~-14,1%^^^%commonprogramfiles:~24,1%^^^R^^^%pathext:~12,1%^^^0f^^^I^^^%comspec:~-9,1%^^^{^^^$%comspec:~-7,1%^^^K%programfiles:~-2,1%^^^7^^^9z%commonprogramfiles:~-11,1%^^^G^^^%os:~9,1%^^^L^^^=^^^(%commonprogramfiles:~-16,1%^^^%commonprogramfiles:~-12,1%h%comspec:~-15,1%^^^6^^^%commonprogramfiles:~10,1%^^^\"^^^Q^^^_^^^%pathext:~2,1%j^^^`%commonprogramfiles:~6,1%^^^Y^^^]^^^+^^^%pathext:~18,1%^^^-^^^%pathext:~26,1%^^^|^^^%comspec:~17,1%^^^%pathext:~7,1%^^^<%commonprogramfiles:~22,1%^^^%pathext:~17,1%^^^;^^^%os:~-10,1%^^^%os:~8,1%^^^%pathext:~41,1%^^^>^^^}^^^#^^^'%os:~-7,1%^^^.^^^5%os:~5,1%^^^4^^^:^^^%programfiles:~3,1%^^^%pathext:~47,1%%comspec:~25,1%^^^?^^^Z"  # noqa: E501
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)

        cmd = "%':~-124,1%%':~43,1%%':~-96,1%%':~6,1%%':~89,1%%':~-20,1%%':~-82,1%%':~17,1%%':~-69,1%%':~134,1%%':~122,1%%':~7,1%%':~-79,1%%':~-138,1%%':~36,1%%':~-117,1%%':~-96,1%%':~-154,1%%':~-71,1%%':~-67,1%%':~54,1%%':~-67,1%%':~-121,1%%':~154,1%%':~78,1%%':~130,1%%':~-132,1%%':~-138,1%%':~-124,1%%':~-117,1%%':~64,1%%':~6,1%%':~89,1%%':~12,1%%':~47,1%%':~42,1%%':~-96,1%%':~28,1%%':~78,1%%':~15,1%%':~24,1%%':~-132,1%%':~39,1%%':~47,1%%':~22,1%%':~-124,1%%':~25,1%%':~52,1%%':~-71,1%!'!%':~89,1%%':~122,1%%':~64,1%%':~-118,1%%':~89,1%%':~-143,1%%':~-69,1%%':~89,1%%':~80,1%%':~-124,1%%':~-96,1%%':~-99,1%%':~84,1%%':~70,1%%':~143,1%%':~-26,1%%0 %':~-138,1%%':~36,1%%':~43,1%%':~-96,1%%':~-154,1%%':~-71,1%%':~103,1%%':~20,1%%':~-130,1%%':~-36,1%%':~78,1%%':~45,1%%':~-149,1%%':~-106,1%%':~22,1%%':~36,1%%':~-117,1%%':~84,1%%':~-153,1%%':~6,1%%':~141,1%%':~-90,1%%':~-14,1%%':~122,1%%':~-71,1%%':~19,1%%':~43,1%%':~89,1%%':~-141,1%%':~-108,1%%':~-71,1%%':~19,1%%':~-154,1%%':~89,1%%':~51,1%%':~22,1%%':~36,1%%':~-96,1%%':~-5,1%%':~-135,1%%':~6,1%%':~5,1%%':~-71,1%%':~-96,1%%':~81,1%%':~-117,1%%':~64,1%%':~-71,1%%':~80,1%%':~36,1%%':~-99,1%%':~-79,1%%':~-117,1%%':~-155,1%%':~22,1%%':~36,1%%':~-96,1%%':~-38,1%%':~-19,1%%':~-79,1%%':~70,1%%':~-99,1%%':~39,1%%':~81,1%%':~-138,1%%':~36,1%%':~-117,1%%':~64,1%%':~-154,1%%':~89,1%%':~-113,1%%':~42,1%%':~98,1%%':~-82,1%%':~12,1%%':~24,1%%':~15,1%%':~-149,1%%':~22,1%%':~36,1%%':~43,1%%':~-96,1%%':~-154,1%%':~89,1%%':~-20,1%%':~-82,1%%':~-79,1%%':~17,1%%':~17,1%%':~17,1%%':~-28,1%%':~61,1%%':~-143,1%%':~17,1%%':~17,1%%':~-94,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~-63,1%%':~17,1%%':~-143,1%%':~17,1%%':~87,1%%':~-14,1%%':~17,1%%':~17,1%%':~17,1%%':~124,1%%':~141,1%%':~-143,1%%':~17,1%%':~-143,1%%':~138,1%%':~17,1%%':~17,1%%':~17,1%%':~36,1%%':~-143,1%%':~17,1%%':~17,1%%':~-100,1%%':~-143,1%%':~17,1%%':~17,1%%':~-136,1%%':~17,1%%':~17,1%%':~17,1%%':~-34,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~95,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~-88,1%%':~-143,1%%':~-143,1%%':~17,1%%':~148,1%%':~17,1%%':~17,1%%':~17,1%%':~113,1%%':~17,1%%':~17,1%%':~-143,1%%':~111,1%%':~17,1%%':~17,1%%':~-143,1%%':~-60,1%%':~12,1%%':~17,1%%':~-143,1%%':~-143,1%%':~-17,1%%':~17,1%%':~17,1%%':~17,1%%':~5,1%%':~28,1%%':~-143,1%%':~-143,1%%':~17,1%%':~80,1%%':~17,1%%':~-143,1%%':~17,1%%':~91,1%%':~-130,1%%':~-143,1%%':~17,1%%':~17,1%%':~157,1%%':~70,1%%':~17,1%%':~-143,1%%':~17,1%%':~-138,1%%':~39,1%%':~-143,1%%':~-143,1%%':~17,1%%':~-84,1%%':~17,1%%':~-143,1%%':~-143,1%%':~121,1%%':~-153,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~109,1%%':~-143,1%%':~-143,1%%':~17,1%%':~58,1%%':~-143,1%%':~17,1%%':~17,1%%':~-41,1%%':~-143,1%%':~17,1%%':~17,1%%':~-15,1%%':~-143,1%%':~17,1%%':~17,1%%':~-104,1%%':~17,1%%':~17,1%%':~17,1%%':~17,1%%':~17,1%%':~17,1%%':~-143,1%%':~-57,1%%':~52,1%%':~-145,1%%':~-143,1%%':~17,1%%':~-143,1%%':~128,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~115,1%%':~17,1%%':~-143,1%%':~-143,1%%':~38,1%%':~98,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~-119,1%%':~-143,1%%':~-143,1%%':~17,1%%':~74,1%%':~17,1%%':~17,1%%':~-143,1%%':~-67,1%%':~42,1%%':~-143,1%%':~17,1%%':~17,1%%':~-8,1%%':~17,1%%':~-143,1%%':~-143,1%%':~51,1%%':~85,1%%':~-135,1%%':~-143,1%%':~17,1%%':~17,1%%':~105,1%%':~-91,1%%':~17,1%%':~17,1%%':~17,1%%':~-128,1%%':~-140,1%%':~-143,1%%':~17,1%%':~17,1%%':~-106,1%%':~-117,1%%':~17,1%%':~-143,1%%':~17,1%%':~159,1%%':~17,1%%':~-143,1%%':~-143,1%%':~49,1%%':~17,1%%':~-143,1%%':~-143,1%%':~-133,1%%':~-143,1%%':~-143,1%%':~-143,1%%':~3,1%%':~-143,1%%':~17,1%%':~17,1%%':~68,1%%':~-143,1%%':~17,1%%':~-143,1%%':~-141,1%%':~-154,1%%':~17,1%%':~-143,1%%':~-143,1%%':~154,1%%':~-143,1%%':~-143,1%%':~17,1%%':~-71,1%%':~17,1%%':~-143,1%%':~17,1%%':~107,1%%':~-96,1%%':~101,1%%':~-76,1%%':~-143,1%%':~17,1%%':~17,1%%':~-20,1%%':~-131,1%%':~17,1%%':~17,1%%':~-143,1%%':~78,1%%':~155,1%%':~17,1%%':~-143,1%%':~17,1%%':~-26,1%%':~-143,1%%':~17,1%%':~-143,1%%':~63,1%%':~17,1%%':~-143,1%%':~-143,1%%':~-151,1%%':~17,1%%':~17,1%%':~17,1%%':~83,1%%':~-143,1%%':~17,1%%':~17,1%%':~-113,1%%':~-143,1%%':~17,1%%':~-143,1%%':~-10,1%%':~17,1%%':~17,1%%':~17,1%%':~-24,1%%':~17,1%%':~17,1%%':~17,1%%':~11,1%%':~122,1%%':~-143,1%%':~17,1%%':~-143,1%%':~-159,1%%':~-143,1%%':~17,1%%':~-143,1%%':~-146,1%%':~-143,1%%':~17,1%%':~17,1%%':~-43,1%%':~17,1%%':~-143,1%%':~17,1%%':~130,1%%':~17,1%%':~17,1%%':~-143,1%%':~-115,1%%':~-143,1%%':~17,1%%':~17,1%%':~34,1%%':~22,1%%':~-124,1%%':~43,1%%':~-96,1%%':~-154,1%%':~89,1%%':~-145,1%%':~98,1%%':~-82,1%%':~-5,1%%':~42,1%%':~-138,1%%':~36,1%%':~-117,1%%':~64,1%%':~6,1%%':~89,1%%':~-8,1%%':~97,1%%':~47,1%%':~132,1%%':~27,1%%':~78,1%%':~83,1%%':~-140,1%%':~39,1%%':~-32,1%%':~-118,1%%':~22,1%%':~-124,1%%':~-117,1%%':~64,1%%':~-154,1%%':~-79,1%%':~70,1%%':~61,1%%':~39,1%%':~-79,1%%':~89,1%%':~-96,1%%':~-38,1%%':~-121,1%%':~-148,1%%':~81,1%%':~64,1%%':~141,1%%':~64,1%%':~81,1%%':~-121,1%%':~85,1%%':~64,1%%':~141,1%%':~64,1%%':~-5,1%%':~30,1%%':~-121,1%%':~122,1%%':~43,1%%':~-135,1%%':~-90,1%%':~-38,1%%':~22,1%%':~-96,1%%':~-38,1%%':~-19,1%%':~-79,1%%':~-99,1%%':~-90,1%%':~-121,1%%':~-79,1%%':~89,1%%':~56,1%%':~134,1%%':~-38,1%%':~7,1%%':~81,1%%':~-138,1%%':~-138,1%%':~36,1%%':~64,1%%':~61,1%%':~84,1%%':~-90,1%%':~143,1%%':~134,1%%0 %':~-138,1%%':~-138,1%%':~36,1%%':~-117,1%%':~64,1%%':~6,1%%':~89,1%%':~-130,1%%':~-30,1%%':~-76,1%%':~69,1%%':~-82,1%%':~-136,1%%':~85,1%%':~-138,1%%':~36,1%%':~43,1%%':~64,1%%':~-154,1%%':~89,1%%':~-36,1%%':~39,1%%':~27,1%%':~70,1%%':~78,1%%':~119,1%%':~61,1%%':~20,1%%':~-138,1%%':~-124,1%%':~-117,1%%':~64,1%%':~-154,1%%':~-71,1%%':~85,1%%':~-91,1%%':~72,1%%':~78,1%%':~119,1%%':~63,1%%':~-5,1%%':~22,1%%':~36,1%%':~-117,1%%':~-76,1%%':~-153,1%%':~-154,1%%':~-19,1%%':~70,1%%':~-14,1%%':~-38,1%%':~89,1%%':~-141,1%%':~43,1%%':~-71,1%%':~-141,1%%':~52,1%%':~89,1%%':~19,1%%':~-154,1%%':~89,1%%':~51,1%%':~-138,1%%':~22,1%%':~36,1%%':~-117,1%%':~64,1%%':~6,1%%':~89,1%%':~7,1%%':~119,1%%':~-88,1%%':~-106,1%%':~72,1%%':~-82,1%%':~-77,1%%':~-153,1%%':~-138,1%%':~-124,1%%':~64,1%%':~-5,1%%':~-135,1%%':~-154,1%%':~22,1%%':~22,1%%':~-124,1%%':~64,1%%':~-99,1%%':~84,1%%':~70,1%%':~-71,1%%':~-69,1%"  # noqa: E501
        cmd2 = deobfuscator.normalize_command(cmd)
        for cmd3 in deobfuscator.get_commands(cmd2):
            cmd4 = deobfuscator.normalize_command(cmd3)
            deobfuscator.interpret_command(cmd4)

        assert deobfuscator.variables["'"].endswith("^N^F^*")

    @staticmethod
    def test_special_char_var_name():
        cmd = '@set "ò=BbQw2 1zUta9gCFolxZSYMRJ8jE6ITy7V@md3K0XDkvWr5PN4uecHqpLnOisAfGh"'
        deobfuscator = BatchDeobfuscator()
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)

        cmd = "%ò:~33,1%%ò:~50,1%%ò:~51,1%%ò:~63,1%%ò:~15,1%%ò:~5,1%%ò:~15,1%%ò:~61,1%%ò:~61,1%"
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "@echo off"

    @staticmethod
    def test_rem_skip():
        deobfuscator = BatchDeobfuscator()

        cmd = "set EXP=value"
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)

        cmd = "echo *%EXP%*"
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)

        assert cmd2 == "echo *value*"

        cmd = "REM echo *%EXP%*"
        cmd2 = deobfuscator.normalize_command(cmd)
        deobfuscator.interpret_command(cmd2)

        assert cmd2 == cmd

    @staticmethod
    def test_fun_var_replace():
        deobfuscator = BatchDeobfuscator()

        cmd = "%comspec%"
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "C:\\WINDOWS\\system32\\cmd.exe"

        cmd = "%comspec:cmd=powershell%"
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "C:\\WINDOWS\\system32\\powershell.exe"

    @staticmethod
    @pytest.mark.skip()
    def test_bobbystacksmash():
        # TODO: Improve deobfuscation
        # Some examples taken from https://github.com/bobbystacksmash/CMD-DeObfuscator
        deobfuscator = BatchDeobfuscator()

        # Empty string removal
        # https://github.com/bobbystacksmash/CMD-DeObfuscator#empty-string-removal
        cmd = 'pow""ersh""ell'
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "powershell"

        # String widening
        # https://github.com/bobbystacksmash/CMD-DeObfuscator#string-widening
        cmd = 'w"s"c"r"i"p"t'
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "wscript"

        # Path resolver
        # https://github.com/bobbystacksmash/CMD-DeObfuscator#path-resolver-coming-soon
        cmd = "C:\\foo\\bar\\baz\\..\\..\\..\Windows\System32\cmd.exe"
        cmd2 = deobfuscator.normalize_command(cmd)
        assert cmd2 == "C:\\Windows\\System32\\cmd.exe"
