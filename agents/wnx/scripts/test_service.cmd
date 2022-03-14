@echo off
rem Simple testing script for any service
rem You may need Administrative Account
rem Usage:
rem     test_service.cmd <binary> CheckMkService
rem Example:
rem     test_service.cmd check_mk_service64.exe CheckMkService
set svc=%1%
set svc_name=%2%
set e=0
%svc% -install
if NOT "%errorlevel%"  == "0" powershell Write-Host "Service Failed to Install" -ForegroundColor red && set e=1 && goto exit
powershell Write-Host "Service Installed" -ForegroundColor green
net start CheckMkService
if NOT "%errorlevel%"  == "0" powershell Write-Host "Service Failed to Start" -ForegroundColor red && set e=1 && goto remove
powershell Write-Host "Service Started" -ForegroundColor green
pause
net stop CheckMkService
if NOT "%errorlevel%"  == "0" powershell Write-Host "Service Failed to Stop" -ForegroundColor red && set e=1 && goto remove
powershell Write-Host "Service Stopped" -ForegroundColor green
:remove
%svc% -remove
if NOT "%errorlevel%"  == "0" powershell Write-Host "Service Failed to Remove" -ForegroundColor red && set e=1 && goto exit
powershell Write-Host "Service Removed" -ForegroundColor green
:exit
exit /b %e%