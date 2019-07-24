@echo off
call prepare_to_tests.cmd
set root=%cd%\..\..\artefacts
set REMOTE_MACHINE=%root%

if "%1" == "SIMULATE_OK" powershell Write-Host "Unit test SUCCESS" -Foreground Green  && exit 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Unit test FAIL" -Foreground Red && del %REMOTE_MACHINE%\check_mk_service.msi && exit 100
if NOT "%1" == "" set param=--gtest_filter=%1
set sec_param=%2
if "%param%" == "" powershell Write-Host "Full and Looooooong test was requested." -Foreground Cyan && set sec_param=both

powershell Write-Host "32-bit test" -Foreground Cyan
cd %REMOTE_MACHINE%
%REMOTE_MACHINE%\watest32.exe %param%
if not %errorlevel% == 0 goto error
cd %REMOTE_MACHINE%
if NOT "%sec_param%" == "both" powershell Write-Host "This is end of testing. QUICK test was requested." -Foreground Cyan && goto success

@rem 64-bit is tested quickly
powershell Write-Host "64-bit test" -Foreground Cyan
if "%1" == "" set param=--gtest_filter=-PluginTest.Sync*:PluginTest.Async*
%REMOTE_MACHINE%\watest64.exe %param%
if not %errorlevel% == 0 goto error
popd
powershell Write-Host "This is end of testing. FULL test was requested." -Foreground Cyan
:success
powershell Write-Host "Unit test SUCCESS" -Foreground Green
goto end
:error
popd
powershell Write-Host "Unit test failed" -Foreground Red 
exit 100
:end
