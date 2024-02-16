@echo off
SETLOCAL EnableDelayedExpansion

@rem Installs all required packages GLOBALLY

if "%1"=="" (
:: Windows method to save output to a variable :(
:: Run default python to find install
powershell Write-Host "Using default python!" -Foreground Yellow
for /f %%i in ('python -c "import os;import sys;print(os.path.dirname(sys.executable))"') do set python_dir=%%i
) else (
powershell Write-Host "Using custom python" -Foreground Green
set python_dir=%1
)

set ppath=%python_dir%
powershell Write-Host "Using directory !ppath!" -Foreground Green
@if not exist !ppath! powershell Write-Host "You have to install 32 bit python in directory !python_dir!" -Foreground Red && exit /B 1

@%ppath%\python -m pip install --upgrade pip > nul 2>&1 
if "%errorlevel%" == "0" (
  powershell Write-Host "Pip Upgraded" -Foreground Green 
) else (
  powershell Write-Host "Pip Upgrade Failed"  -Foreground Red
)

set uniqueFileName=%tmp%\bat~%RANDOM%.tmp

set packages=pyinstaller future pipenv pyyaml pypiwin32  requests  pyOpenSSL requests[socks] pathlib pathlib2 typing pytest time-machine bs4 black isort pytest-mock telnetlib3 asyncio marshmallow

%ppath%\python -m pip install %packages% > %uniqueFileName%
if "%errorlevel%" == "0" (
  powershell Write-Host "Installed" -Foreground Green 
) else (
  powershell Write-Host "Failed"  -Foreground Red
  type %uniqueFileName%
)
