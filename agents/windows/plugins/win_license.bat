@echo off
set CMK_VERSION="2.2.0i1"
REM ***
REM * plugin to gather and output Windows activation status
REM ***

echo ^<^<^<win_license^>^>^>
cscript //NoLogo %windir%/System32/slmgr.vbs /dli
