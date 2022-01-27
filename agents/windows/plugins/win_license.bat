@echo off
set CMK_VERSION="2.1.0i1"
REM ***
REM * plugin to gather and output Windows activation status
REM ***

echo ^<^<^<win_license^>^>^>
if not exist "%temp%\slmgr.vbs" (
    copy "%windir%\system32\slmgr.vbs" "%temp%\slmgr.vbs" > NUL
)

if exist "%temp%\slmgr.vbs" (
    cscript //NoLogo "%temp%\slmgr.vbs" /dli
    del "%temp%\slmgr.vbs" > NUL
)
