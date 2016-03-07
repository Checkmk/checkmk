@ECHO off & setlocal EnableDelayedExpansion

REM customize rstcli to your needs
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

