@echo off
REM
REM plugin to gather and output Windows activation status
REM

echo ^<^<^<win_license^>^>^>
cscript //NoLogo %windir%/System32/slmgr.vbs /dli
