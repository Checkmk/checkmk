@echo off
:: File to run Regression Tests in the tests/regression folder
:: should be called after successful build with correct artifacts

set cur_dir=%cd%
set WNX_TEST_ROOT=%temp%\test_i_%random%
mkdir %WNX_TEST_ROOT%
::net stop checkmkservice
set arte=%cur_dir%\..\..\artefacts
set results=regression_tests_results.zip

powershell Write-Host "Windows agent Regression Tests are starting in %WNX_TEST_ROOT%" -Foreground Cyan

:: Prepare test folder for testing
mkdir %WNX_TEST_ROOT%\test\root\plugins
mkdir %WNX_TEST_ROOT%\test\data
copy %arte%\check_mk_agent.exe  %WNX_TEST_ROOT%\check_mk_agent.exe >nul
copy %arte%\check_mk.yml %WNX_TEST_ROOT%\test\root\check_mk.yml >nul
powershell Remove-NetFirewallRule -DisplayName "AllowRegression" 2>nul
powershell New-NetFirewallRule -DisplayName "AllowRegression" -Direction Inbound -Program %WNX_TEST_ROOT%\check_mk_agent.exe -RemoteAddress LocalSubnet -Action Allow >nul
xcopy ..\windows\plugins\*.* %WNX_TEST_ROOT%\test\root\plugins /D /Y> nul
:: Testing
cd tests\regression
:: tests wait for this env variable
set WNX_REGRESSION_BASE_DIR=%WNX_TEST_ROOT%
set WNX_INTEGRATION_BASE_DIR=
py -3 -m pytest %* || set failed=1
powershell Remove-NetFirewallRule -DisplayName "AllowRegression" >nul

call :zip_results
cd %cur_dir%
if "%failed%" == "1" (
powershell Write-Host "Regression Test Failed" -Foreground Red 
exit /b 81
)
powershell Write-Host "Regression Test Success" -Foreground Green
exit /b 0


:zip_results
del %arte%\%results% 2> nul
pushd %WNX_TEST_ROOT% && ( call :zip_and_remove & popd )
exit /b

:zip_and_remove
7z a -r -y -tzip %arte%\%results% >nul 
rmdir /s/q "%WNX_TEST_ROOT%" 2>nul
exit /b
