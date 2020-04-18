@rem  Builds venv
@rem  May be called only from exec_cmd.bat

@echo off
powershell Write-Host "Building venv" -foreground cyan
if not defined work_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 3
if not exist %work_dir% powershell Write-Host "%work_dir% doesnt exist" -foreground red && exit /b 4
cd %work_dir% || powershell Write-Host "Failed enter %work_dir%" -foreground red && exit /b 5
set PIPENV_VENV_IN_PROJECT=true
%install_dir%\python.exe -m pipenv sync
powershell Write-Host "venv is ready" -foreground green
