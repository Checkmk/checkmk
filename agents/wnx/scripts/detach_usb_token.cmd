@echo off
::
:: File to detach some usb token with YK

if "%1" == "" powershell Write-Host "Invalid usbip" -ForegroundColor Red && goto usage

@%1 detach -p 00
IF %ERRORLEVEL% NEQ 0 powershell Write-Host "Failed to detach" -ForegroundColor Yellow & exit /b 0
powershell Start-Sleep -Seconds 2
powershell Write-Host "Detached!" -ForegroundColor Green
exit /b 0


:usage
powershell Write-Host "Usage:" -ForegroundColor DarkGreen
powershell Write-Host "detach_usb_token.cmd usb_ip_path" -ForegroundColor DarkGreen
powershell Write-Host "Example:" -ForegroundColor DarkGreen
powershell Write-Host "       detach_usb_token.cmd c:\common\usb_ip\usbip.exe" -ForegroundColor DarkGreen
:exit
