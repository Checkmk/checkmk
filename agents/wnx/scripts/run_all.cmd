@echo off
@call test_service.cmd check_mk_service64.exe CheckMkService
if NOT "%errorlevel%"  == "0" powershell Write-Host "Test Failed" -ForegroundColor red && set e=1 && goto exit
powershell Write-Host "Test Successful" -ForegroundColor green
:exit
