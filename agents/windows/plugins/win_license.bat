@echo off
set CMK_VERSION="2.1.0b1"
REM ***
REM * plugin to gather and output Windows activation status
REM ***

echo ^<^<^<win_license^>^>^>
cscript //NoLogo %windir%/System32/slmgr.vbs /dli
