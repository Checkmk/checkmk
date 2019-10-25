@echo off

@rem Installs all required packages GLOBALLY

set ppath=C:\Python27\Scripts
@C:\Python27\Scripts\pip install --upgrade pip > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "Pip Upgraded" -Foreground Green 
) else (
  powershell Write-Host "Pip Upgrade Failed"  -Foreground Red
)
@%ppath%\pip install pyinstaller > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "pyinstaller installed" -Foreground Green 
) else (
  powershell Write-Host "pyinstaller install Failed"  -Foreground Red
)
@%ppath%\pip install yapf > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "yapf installed" -Foreground Green 
) else (
  powershell Write-Host "yapf install Failed"  -Foreground Red
)

@%ppath%\pip install future> nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "future installed" -Foreground Green 
) else (
  powershell Write-Host "future install Failed"  -Foreground Red
)

@%ppath%\pip install pipenv> nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "pipenv installed" -Foreground Green 
) else (
  powershell Write-Host "pipenv install Failed"  -Foreground Red
)

call python_package_install %ppath% pyyaml
call python_package_install %ppath% pypiwin32
call python_package_install %ppath% requests
call python_package_install %ppath% pyOpenSSL
call python_package_install %ppath% requests[socks]
