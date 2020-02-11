@rem Makes lock file
@rem May be called only from exec_cmd.bat

@echo off
powershell Write-Host "Building piplock" -foreground cyan

if not defined install_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not defined work_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 3
if not exist %install_dir% powershell Write-Host "%install_dir% doesnt exist" -foreground red && exit /b 4

mkdir %work_dir% 2> nul
cd %work_dir% || powershell Write-Host "Failed enter %work_dir%" -foreground red && exit /b 5

set PIPENV_VENV_IN_PROJECT=true
%install_dir%\python.exe --version
%install_dir%\python.exe -m pipenv lock 
if not %errorlevel% == 0 powershell Write-Host "Python lock failed" -foreground Red && exit /b 34

powershell Write-Host "Pipfile is locked" -foreground green
