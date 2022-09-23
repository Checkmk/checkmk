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
set arte=%cur_dir%\..\..\artefacts
set CHECKMK_GIT_DIR=%cur_dir%\..\..\

powershell Write-Host "Windows agent Plugin Tests are starting" -Foreground Cyan
py -3 -m pytest tests\ap\test_mk_logwatch_win.py || set failed=1

if "%failed%" == "1" (
powershell Write-Host "Test Failed" -Foreground Red 
exit /b 1
)
powershell Write-Host "Test Success" -Foreground Green
exit /b 0
exit /b
