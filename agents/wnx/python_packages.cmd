@echo off
SETLOCAL EnableDelayedExpansion

@rem Installs all required packages GLOBALLY

if "%1"=="" (
set ppath=C:\Python27.32\Scripts
powershell Write-Host "Using default directory !ppath!" -Foreground Green
) else (
set ppath=%1\Scripts
powershell Write-Host "Using directory !ppath!" -Foreground Green
)

@if not exist !ppath! powershell Write-Host "You have to install 32 bit python in directory !ppath!" -Foreground Red && exit /B 1

@%ppath%\pip install --upgrade pip > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "Pip Upgraded" -Foreground Green 
) else (
  powershell Write-Host "Pip Upgrade Failed"  -Foreground Red
)
@!ppath!\pip install pyinstaller > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "pyinstaller installed" -Foreground Green 
) else (
  powershell Write-Host "pyinstaller install Failed"  -Foreground Red
)
@!ppath!\pip install yapf > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "yapf installed" -Foreground Green 
) else (
  powershell Write-Host "yapf install Failed"  -Foreground Red
)

@!ppath!\pip install future> nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "future installed" -Foreground Green 
) else (
  powershell Write-Host "future install Failed"  -Foreground Red
)

@!ppath!\pip install pipenv> nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "pipenv installed" -Foreground Green 
) else (
  powershell Write-Host "pipenv install Failed"  -Foreground Red
)

call python_package_install !ppath! pyyaml
call python_package_install !ppath! pypiwin32
call python_package_install !ppath! requests
call python_package_install !ppath! pyOpenSSL
call python_package_install !ppath! requests[socks]
call python_package_install !ppath! pathlib
call python_package_install !ppath! pathlib2
call python_package_install !ppath! typing
call python_package_install !ppath! pytest
call python_package_install !ppath! freezegun
call python_package_install !ppath! bs4
call python_package_install !ppath! pycryptodomex
