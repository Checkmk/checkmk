:: Pip Upgrading script
:: May be called only from exec_cmd.bat

@echo off
powershell Write-Host "Upgrading pip" -foreground cyan
if not defined install_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %install_dir% powershell Write-Host "%install_dir% doesnt exist" -foreground red && exit /b 3
cd %install_dir%
.\python.exe -m pip install --upgrade pip
powershell Write-Host "Pip upgraded" -foreground green
exit /b 0
