@echo off
rem File to run Integration Tests in the integration folder
rem should be called ONLY after successful build

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
cd integration 
net stop checkmkservice
mkdir %arte%\plugins
py.test %1 || powershell Write-Host "Integration Test Failed" -Foreground Red && cd .. && exit 39
