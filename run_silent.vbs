' 콘솔 창 없이 camp_check.py 를 실행 (윈도우 작업 스케줄러가 이 파일을 호출)
Dim sh, here
Set sh = CreateObject("WScript.Shell")
here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.CurrentDirectory = here
sh.Run "pythonw.exe """ & here & "camp_check.py""", 0, False
