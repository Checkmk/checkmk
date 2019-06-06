@echo off
rem File to run Integration Tests in the integration folder
rem should be called ONLY after successful build

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
cd integration 
py.test || powershell Write-Host "Integration Test Failed" -Foreground Red && cd .. && exit 39
