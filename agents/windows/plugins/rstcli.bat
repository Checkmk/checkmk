@ECHO off & setlocal EnableDelayedExpansion
set CMK_VERSION="2.0.0p22"
REM ***
REM * plugin to to monitor Intel RST raids
REM * customize StorCli path to your needs
REM ***

SET "rstcli=!ProgramFiles!\rstcli\rstcli64.exe"
SET "rstcli_x86=!ProgramFiles!\rstcli\rstcli.exe"

ECHO ^<^<^<rstcli:sep(58)^>^>^>
IF EXIST !rstcli! (
    !rstcli! --information --volume
) ELSE IF EXIST !rstcli_x86! (
    !rstcli_x86! --information --volume
) ELSE (
    ECHO rstcli not found
)

