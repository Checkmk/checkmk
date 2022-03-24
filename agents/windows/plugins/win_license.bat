@echo off
set CMK_VERSION="2.1.0b4"
REM ***
REM * plugin to gather and output Windows activation status
REM ***

echo ^<^<^<win_license^>^>^>

REM create a copy of slmgr.vbs outside the system32 folder to force english text output, because this way the language files can't be found anymore
copy /Y "%windir%\system32\slmgr.vbs" "%temp%\checkmk_slmgr.vbs" > NUL

if exist "%temp%\checkmk_slmgr.vbs" (
    cscript //NoLogo "%temp%\checkmk_slmgr.vbs" /dli
    del "%temp%\checkmk_slmgr.vbs" > NUL
) else (
    REM fallback in case temp directory cannot be written to
    cscript //NoLogo "%windir%\System32\slmgr.vbs" /dli
)
