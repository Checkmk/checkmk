:: Uninstall Python
:: May be called only from exec_cmd.bat

@echo off
if not defined pexe_uninstall powershell Write-Host "This script must be called with exec_cmd.bat" -foreground Red && exit /b 5
powershell Write-Host "Uninstalling Python ..." -foreground Cyan 
if not exist %pexe_uninstall% powershell Write-Host "Python was not correctly installed" -foreground Green && exit /b 0
%pexe_uninstall% /uninstall /quiet
powershell Write-Host "Python uninstalled" -foreground Green
exit /b 0

