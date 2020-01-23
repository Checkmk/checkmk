@echo off
set p_full_name=python-3.8.1
powershell Write-Host "Uninstalling Python ..." -foreground Cyan 
if not exist %pexe_uninstall% powershell Write-Host "Python was not correctly installed" -foreground Green && exit /b 0
%pexe_uninstall% /uninstall /quiet
powershell Write-Host "Python uninstalled" -foreground Green

