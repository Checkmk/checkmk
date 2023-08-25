@echo off
::
:: File to attach some usb token with YK

if "%1" == "" powershell Write-Host "Invalid usbip" -ForegroundColor Red && goto usage
if "%2" == "" powershell Write-Host "Invalid server" -ForegroundColor Red && goto usage
if "%3" == "" powershell Write-Host "Invalid port" -ForegroundColor Red && goto usage
if "%4" == "" powershell Write-Host "Invalid control script" -ForegroundColor Red && goto usage

@powershell -ExecutionPolicy ByPass -File %4 %1 %2 %3
IF %ERRORLEVEL% NEQ 0 powershell Write-Host "Failed" -ForegroundColor Red & exit /b 1
powershell Start-Sleep -Seconds 5
powershell Write-Host "Attached!" -ForegroundColor Green
%1 port
exit /b 0


:usage
powershell Write-Host "Usage:" -ForegroundColor DarkGreen
powershell Write-Host "attach_usb_token.cmd usb_ip_path usb_server port script" -ForegroundColor DarkGreen
powershell Write-Host "Example:" -ForegroundColor DarkGreen
powershell Write-Host "       attach_usb_token.cmd c:\common\usb_ip\usbip.exe yubi-usbserver.lan.checkmk.net 1-1.2 scripts\attach.ps1" -ForegroundColor DarkGreen
:exit
