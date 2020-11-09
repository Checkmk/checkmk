set VERSION="2.0.0i2"
@ECHO off & setlocal EnableDelayedExpansion
REM ***
REM * plugin to to monitor RAID status via StorCLI utility
REM * customize StorCli path to your needs
REM ***

SET "StorCli=C:\Program Files\StorCLI\storcli64.exe"

IF NOT EXIST !StorCli! GOTO END

ECHO ^<^<^<storcli_pdisks^>^>^>
"!StorCli!" /call/eall/sall show
ECHO ^<^<^<storcli_vdrives^>^>^>
"!StorCli!" /call/vall show

:END
