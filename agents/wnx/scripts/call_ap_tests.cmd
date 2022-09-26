@echo off
::
:: File to run Integration Tests in the tests/integration folder
:: Should be called after successful build with correct artifacts
::
:: local testing code below
::set arte=c:\Users\sk\git\check_mk\artefacts
::set WNX_INTEGRATION_BASE_DIR=c:\Users\sk\git\check_mk\agents\wnx\build\integration
::set DEBUG_HOME_DIR=c:\Users\sk\git\check_mk\agents\wnx\build\integration\test\data
::pytest -v -s tests/integration/test_check_mk_run.py

set cur_dir=%cd%

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
