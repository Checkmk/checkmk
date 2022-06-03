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
set WNX_INTEGRATION_BASE_DIR=%temp%\test_wnx_%random%
set DEBUG_HOME_DIR=%WNX_INTEGRATION_BASE_DIR%\test\data
set WNX_TEST_ROOT=%WNX_INTEGRATION_BASE_DIR%\test\root
set arte=%cur_dir%\..\..\artefacts
set results=integration_tests_ng_results.zip

powershell Write-Host "Windows agent Integration Tests are starting in %WNX_INTEGRATION_BASE_DIR%" -Foreground Cyan

:: Firewall processing
echo fw rule - AllowIntegration1
powershell Remove-NetFirewallRule -DisplayName "AllowIntegration1" 2>nul
powershell New-NetFirewallRule -DisplayName "AllowIntegration1" -Direction Inbound -Program %WNX_TEST_ROOT%\check_mk_agent.exe -RemoteAddress LocalSubnet -Action Allow >nul
echo fw rule - AllowIntegration2
powershell Remove-NetFirewallRule -DisplayName "AllowIntegration2" 2>nul
powershell New-NetFirewallRule -DisplayName "AllowIntegration2" -Direction Inbound -Program %DEBUG_HOME_DIR%\bin\cmk-agent-ctl.exe -RemoteAddress LocalSubnet -Action Allow >nul

:: TEST!
py -3 -m pytest tests\integration\%* || set failed=1

:: Firewall processing again
echo fw rules deletion...
powershell Remove-NetFirewallRule -DisplayName "AllowIntegration1" 2>nul
powershell Remove-NetFirewallRule -DisplayName "AllowIntegration2" 2>nul

call :zip_results
if "%failed%" == "1" (
powershell Write-Host "Integration Test Failed" -Foreground Red 
exit /b 0
)
powershell Write-Host "Integration Test Success" -Foreground Green
exit /b 0

:: NOT REACHABLE
:zip_results
echo backing up %arte%\%results% ...
ren %arte%\%results% %arte%\%results%.sav 2>nul
echo switch to "%WNX_INTEGRATION_BASE_DIR%"
dir "%WNX_INTEGRATION_BASE_DIR%"
pushd "%WNX_INTEGRATION_BASE_DIR%" && ( call :zip_and_remove & popd )
exit /b

:zip_and_remove
echo zipping results...
7z a -r -y -tzip %arte%\%results% >nul 
echo cleaning...
rmdir /s/q "%WNX_INTEGRATION_BASE_DIR%" 2>nul
rmdir "%WNX_INTEGRATION_BASE_DIR%" 2>nul
exit /b
