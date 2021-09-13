@echo off
:: File to run Integration Tests in the integration folder
:: should be called ONLY after successful build
:: checkmkservice wil be stopped if any

set cur_dir=%cd%
set WNX_TEST_I_ROOT=%temp%\test_i_%random%
mkdir %WNX_TEST_I_ROOT%
net stop checkmkservice
set arte=%cur_dir%\..\..\artefacts
:: Prepare test folder for testing
mkdir %WNX_TEST_I_ROOT%\test\root\plugins
mkdir %WNX_TEST_I_ROOT%\test\data
mklink %WNX_TEST_I_ROOT%\check_mk_agent.exe %arte%\check_mk_agent.exe
mklink %WNX_TEST_I_ROOT%\test\root\check_mk.yml %arte%\check_mk.yml
powershell New-NetFirewallRule -DisplayName "AllowIntegration" -Direction Inbound -Program %WNX_TEST_I_ROOT%\check_mk_agent.exe -RemoteAddress LocalSubnet -Action Allow
xcopy ..\windows\plugins\*.* %WNX_TEST_I_ROOT%\test\root\plugins /D /Y> nul
:: Testing
cd integration 
py -3 -m pytest %* || set failed=1
echo cleaning
cd %WNX_TEST_I_ROOT%
if "%cd%"=="%WNX_TEST_I_ROOT%" (
  del /f/q/s *.* > nul
)
rd /s /q %WNX_TEST_I_ROOT%
rd %WNX_TEST_I_ROOT%
powershell Remove-NetFirewallRule -DisplayName "AllowIntegration"
cd %cur_dir%
if "%failed%" == "1" (
powershell Write-Host "Integration Test Failed" -Foreground Red 
exit /b 0
)
powershell Write-Host "Integration Test Success" -Foreground Green
exit /b 0


