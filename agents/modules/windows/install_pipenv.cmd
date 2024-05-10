:: pipenv installer script
:: May be called only from exec_cmd.bat

@echo off
powershell Write-Host "Installing pipenv" -foreground cyan
if not defined install_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %install_dir% powershell Write-Host "%install_dir% doesnt exist" -foreground red && exit /b 3
cd %install_dir%
powershell Write-Host "Pipenv installing..." -foreground green
.\python.exe -m pip install pipenv

:: As for 19.03.2019 we must use virtualenv 20.0.10
powershell Write-Host "virtualenv resetting to the correct version..." -foreground green
.\python.exe -m pip install virtualenv
powershell Write-Host "Pipenv installed" -foreground green
exit /b 0
