@echo off
powershell Write-Host "Installing pipenv" -foreground cyan
if not defined install_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %install_dir% powershell Write-Host "%install_dir% doesnt exist" -foreground red && exit /b 3
cd %install_dir%
.\python.exe -m pip install pipenv
powershell Write-Host "Pipenv installed" -foreground green
