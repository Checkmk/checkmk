@echo off
set CMK_VERSION="2.4.0p21"
REM ***
REM * plugin to gather and output Windows activation status
REM ***

echo ^<^<^<win_license^>^>^>

set "CMK_TMP=%SystemDrive%\ProgramData\checkmk\agent\tmp"

REM create a copy of slmgr.vbs outside the system32 folder to force english text output, because this way the language files can't be found anymore
copy /Y "%windir%\system32\slmgr.vbs" "%CMK_TMP%\checkmk_slmgr.vbs" > NUL

if exist "%CMK_TMP%\checkmk_slmgr.vbs" (
    cscript //NoLogo "%CMK_TMP%\checkmk_slmgr.vbs" /dli
    del "%CMK_TMP%\checkmk_slmgr.vbs" > NUL
) else (
    REM fallback in case temp directory cannot be written to
    cscript //NoLogo "%windir%\System32\slmgr.vbs" /dli
)
