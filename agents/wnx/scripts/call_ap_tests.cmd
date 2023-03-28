@echo off
::
:: File to run Agent Plugins Integration Tests
::
:: local testing code below
::set arte=c:\Users\sk\git\check_mk\artefacts
::set WNX_INTEGRATION_BASE_DIR=c:\Users\sk\git\check_mk\agents\wnx\build\integration
::set DEBUG_HOME_DIR=c:\Users\sk\git\check_mk\agents\wnx\build\integration\test\data
::pytest -v -s tests/integration/test_check_mk_run.py

if "%cur_dir%" == "" powershell Write-Host "cur_dir not defined" -Foreground Red & exit /b 1
if "%arte%" == "" powershell Write-Host "arte not defined" -Foreground Red & exit /b 1
if "%CHECKMK_GIT_DIR%" == "" powershell Write-Host "CHECKMK_GIT_DIR not defined" -Foreground Red & exit /b 1

powershell Write-Host "Windows agent Plugin Tests are starting" -Foreground Cyan
if "%CHECKMK_GIT_DIR%" == "" (
powershell Write-Host "Test Failed: variable CHECKMK_GIT_DIR is not set" -Foreground Red
exit /b 1
)
chdir "%CHECKMK_GIT_DIR%" || ( echo "can't change dir to root" && exit /b 1 )
set WNX_DIR=%CHECKMK_GIT_DIR%\agents\wnx

py -3 -m pytest %WNX_DIR%\tests\ap\test_mk_logwatch_win.py || set failed=1

if "%failed%" == "1" (
powershell Write-Host "Test Failed" -Foreground Red 
exit /b 1
)
powershell Write-Host "Test Success" -Foreground Green
exit /b 0
