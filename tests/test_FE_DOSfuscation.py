# Tests coming from the FireEye DOSfuscation research
# https://www.fireeye.com/content/dam/fireeye-www/blog/pdfs/dosfuscation-report.pdf
import pytest

from batch_deobfuscator.batch_interpreter import BatchDeobfuscator


class TestUnittests:
    @staticmethod
    @pytest.mark.parametrize(
        "logical_line, result",
        [
            (",;,cmd.exe,;,/c,;,echo;Command 1&&echo,Command 2", ["cmd.exe   /c   echo Command 1", "echo Command 2"]),
        ],
    )
    def test_comma_semi_colon(logical_line, result):
        deobfuscator = BatchDeobfuscator()
        commands = deobfuscator.get_commands(logical_line)
        res = []
        for command in commands:
            normalized_comm = deobfuscator.normalize_command(command)
            deobfuscator.interpret_command(normalized_comm)
            res.append(normalized_comm)

        assert len(res) == len(result)
        for test_res, expected_res in zip(res, result):
            assert test_res == expected_res

    @staticmethod
    @pytest.mark.parametrize(
        "statement, result",
        [
            # Substring
            ("%COMSPEC%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~0%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~0,27%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~-7%", "cmd.exe"),
            ("%COMSPEC:~-27%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~-7,-4%", "cmd"),
            ("%COMSPEC:~-27,27%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~-7,3%", "cmd"),
            ("%COMSPEC:~0,1337%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~-1337%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~-1337,1337%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:~-40,3%", "C:\\"),
            ("%COMSPEC:~-1,1%", "e"),
            # Substitution
            ("%COMSPEC:\\=/%", "C:/WINDOWS/system32/cmd.exe"),
            ("%COMSPEC:KeepMatt=Happy%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:*System32\\=%", "cmd.exe"),
            ("%COMSPEC:*Tea=Coffee%", "C:\\WINDOWS\\system32\\cmd.exe"),
            ("%COMSPEC:*e=z%", "zm32\\cmd.exe"),
            ("%COMSPEC:*e=Z%", "Zm32\\cmd.exe"),
            ("%COMSPEC:s=z%", "C:\\WINDOWz\\zyztem32\\cmd.exe"),
            ("%COMSPEC:s=%", "C:\\WINDOW\\ytem32\\cmd.exe"),
            ("%COMSPEC:*S=A%", "A\\system32\\cmd.exe"),
            ("%COMSPEC:*s=A%", "A\\system32\\cmd.exe"),
            ("%COMSPEC:cMD=BlA%", "C:\\WINDOWS\\system32\\BlA.exe"),
            # spacing
            ("%coMSPec:~   -7,    +3%", "cmd"),
            ("%coMSPec:~    -7, +3%", "cmd"),
            # tabs
            ("%coMSPec:~	-7,	+3%", "cmd"),
            # set
            ("%comspec:~-16,1%%comspec:~-1%%comspec:~-13,1%", "set"),
        ],
    )
    def test_variable_manipulation(statement, result):
        deobfuscator = BatchDeobfuscator()
        res = deobfuscator.normalize_command(statement)
        assert res == result

    @staticmethod
    @pytest.mark.parametrize(
        "logical_line, result",
        [
            (
                "s^et g^c^=^er^s&&s^e^t ^tf=^he^ll&&set^ f^a^=^pow&&^s^et^ dq^=C:\\WINDOWS\\System32\\W^i^n^do^ws^!fa^!^!g^c^!!^t^f^!\\^v^1^.0\\^!^fa!^!^gc!!^tf^!&&^ech^o^ hos^tname^;^ ^ | !dq! -^no^p^ ^-",
                [
                    "set gc=ers",
                    "set tf=hell",
                    "set fa=pow",
                    "set dq=C:\\WINDOWS\\System32\\Windowspowershell\\v1.0\\powershell",
                    "echo hostname;",
                    "C:\\WINDOWS\\System32\\Windowspowershell\\v1.0\\powershell -nop -",
                ],
            )
        ],
    )
    def test_echo_pipe(logical_line, result):
        # Could not reproduce exactly what the example is on page 22, but trying something similar.
        # The special characters && needs not to be preceeded by ^, or cut by ^.
        # The special character | needs not to be preceeded or followed by ^
        deobfuscator = BatchDeobfuscator()
        commands = deobfuscator.get_commands(logical_line)
        res = []
        for command in commands:
            normalized_comm = deobfuscator.normalize_command(command)
            deobfuscator.interpret_command(normalized_comm)
            res.append(normalized_comm)

        assert len(res) == len(result)
        for test_res, expected_res in zip(res, result):
            assert test_res == expected_res

    @staticmethod
    @pytest.mark.parametrize(
        "logical_line, result",
        [
            ("set com=netstat /ano&&call %com%", ["set com=netstat /ano", "call netstat /ano"]),
            ("set com=netstat /ano&&cmd /c %com%", ["set com=netstat /ano", "cmd /c netstat /ano"]),
            # Disabled because we are currently returning an empty string on non-found variable, which breaks the
            # declaration of !!#**#!! in this case. We'd need to track EnableDelayedExpansion to make it better too.
            # (
            #     "set --$#$--= /ano&&set !!#**#!!=stat&&set .........=net&&call set ''''''''' ''''''=%.........%%!!#**#!!%%--$#$--% &&call %''''''''' ''''''%",
            #     [
            #         "set --$#$--= /ano",
            #         "set !!#**#!!=stat",
            #         "set .........=net",
            #         "call set ''''''''' ''''''=netstat /ano",
            #         "call netstat /ano",
            #     ],
            # ),
            (
                "set '		= /ano&&set '	=stat&& set '	 =net&&call set '   =%'	 %%'	%%'		%&&call %'   %",
                ["set '		= /ano", "set '	=stat", "set '	 =net", "call set '   =netstat /ano", "call netstat /ano"],
            ),
            (
                "set command=neZsZ7Z /7no&&set sub2=!command:7=a!&&set sub1=!sub2:Z=t!&&CALL %sub1%",
                ["set command=neZsZ7Z /7no", "set sub2=neZsZaZ /ano", "set sub1=netstat /ano", "CALL netstat /ano"],
            ),
        ],
    )
    def test_call_var(logical_line, result):
        deobfuscator = BatchDeobfuscator()
        commands = deobfuscator.get_commands(logical_line)
        res = []
        for command in commands:
            normalized_comm = deobfuscator.normalize_command(command)
            deobfuscator.interpret_command(normalized_comm)
            res.append(normalized_comm)

        assert len(res) == len(result)
        for test_res, expected_res in zip(res, result):
            assert test_res == expected_res

    @staticmethod
    def test_empty_var():
        # Taken from https://i.blackhat.com/briefings/asia/2018/asia-18-bohannon-invoke_dosfuscation_techniques_for_fin_style_dos_level_cmd_obfuscation.pdf page 48
        # This is one of those weird use-case where EnableDelayedExpansion does a bit difference.
        # With EnableDelayedExpansion ON, we lose the ! at the end
        # With EnableDelayedExpansion OFF, we keep the ! at the end
        deobfuscator = BatchDeobfuscator()
        logical_line = 'ec%a%ho "Fi%b%nd Ev%c%il!"'
        expected = 'echo "Find Evil!"'
        normalized_comm = deobfuscator.normalize_command(logical_line)
        assert expected == normalized_comm

    @staticmethod
    @pytest.mark.skip()
    @pytest.mark.parametrize(
        "logical_line",
        [
            ("""FOR /F "delims=s\\ tokens=4" %%a IN ('set^|findstr PSM') DO %%a hostname"""),
            ("""FOR /F "delims=.M tokens=3" %%a IN ('assoc^|findstr lMo') DO %%a hostname"""),
            ("""FOR /F "delims=s\\ tokens=8" %%a IN ('ftype^|findstr lCo') DO %%a hostname"""),
        ],
    )
    def test_FOR_execution(logical_line):
        """
        This resolves to starting powershell and calling hostname:
        FOR /F "delims=s\ tokens=4" %%a IN ('set^|findstr PSM') DO %%a hostname

        You can also get string manipulation out of the "assoc" or "ftype" command to build out the word "powershell"
        """

    @staticmethod
    @pytest.mark.skip()
    @pytest.mark.parametrize(
        "logical_line",
        [
            (
                "set unique=nets /ao&&FOR %A IN (0 1 2 3 2 6 2 4 5 6 0 7 1337) DO set final=!final!!unique:~%A,1!&& IF %A==1337 CALL !final:~-12!"
            ),
            (
                "set unique=nets /ao&&FOR %A IN (0 1 2 3 2 6 2 4 5 6 0 7 1337) DO set final=!final!!unique:~%A,1!&& IF %A==1337 CALL !final:~7!"
            ),
            (
                "set unique=nets /ao&&FOR %A IN (0 1 2 3 2 6 2 4 5 6 0 7 1337) DO set final=!final!!unique:~%A,1!&& IF %A==1337 CALL %final:*final!=%"
            ),
            (
                "((sE^T ^ unIQ^uE=OnBeFt^UsS C/AaToE ))&&,; fo^R;,;%^a,;; i^N;,,;( ,+1; 3 5 7 +5 1^3 +5,,9 11 +1^3 +1;;+15 ^+13^37;,),;,;d^O,,(;(;s^Et fI^Nal=!finAl!!uni^Que:~ %^a,1!))&&(;i^F,%^a=^=+13^37,(Ca^lL;%fIn^Al:~-12%))"
            ),
        ],
    )
    def test_call_var_for(logical_line):
        """
        set unique=nets /ao&&FOR %A IN (0 1 2 3 2 6 2 4 5 6 0 7 1337) DO set final=!final!!unique:~%A,1!&& IF %A==1337 CALL %final:~-12%
        set unique=nets /ao&&FOR %A IN (0 1 2 3 2 6 2 4 5 6 0 7 1337) DO set final=!final!!unique:~%A,1!&& IF %A==1337 CALL %final:~7%
        set unique=nets /ao&&FOR %A IN (0 1 2 3 2 6 2 4 5 6 0 7 1337) DO set final=!final!!unique:~%A,1!&& IF %A==1337 CALL %final:*final!=%%
        ,;c^Md;/^V^:O^N;,;/^C “((sE^T ^ unIQ^uE=OnBeFt^UsS C/AaToE ))&&,; fo^R;,;%^a,;; i^N;,,;( ,+1; 3 5 7 +5 1^3 +5,,9 11 +1^3 +1;;+15 ^+13^37;,),;,;d^O,,(;(;s^Et fI^Nal=!finAl!!uni^Que:~ %^a,1!))&&(;i^F,%^a=^=+13^37,(Ca^lL;%fIn^Al:~-12%))”
        """

    @staticmethod
    @pytest.mark.skip()
    def test_set_reverse():
        """
        cmd /V:ON /C “set reverse=ona/ tatsten&& FOR /L %A IN (11 -1 0) DO set final=!final!!reverse:~%A,1!&&IF %A==0 CALL %final:~-12%”

        cmd /v /r "set reverse=OoBnFaU/S CtAaTtIsOtNe!n&&FOR /L %A IN (23 -2 1) DO set final=!final!!reverse:~%A,1!&&IF %A==1 CALL %final:~-12%"

        ,;c^Md;/^V^:O^N;,;/C “((sE^T reVEr^sE=OoBnFaU/S CtAa^TtIsOtNe!n))&&,; fo^R;,;/L,;,%^a,;; i^N;,,;( ,+23; -2;;+1;,) ,;,;d^O,,(;(;s^Et fI^Nal=!finAl!!rev^Erse:~%^a,1!))&& (;i^F,%^a=^=^1,(Ca^lL;%fIn^Al:~-12%))”
        """
