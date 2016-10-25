@ECHO off & setlocal EnableDelayedExpansion

REM customize StorCli path to your needs
SET "StorCli=C:\Program Files\StorCLI\storcli64.exe"

IF NOT EXIST !StorCli! GOTO END

ECHO ^<^<^<storcli_pdisks^>^>^>
"!StorCli!" /call/eall/sall show
ECHO ^<^<^<storcli_vdrives^>^>^>
"!StorCli!" /call/vall show

:END
