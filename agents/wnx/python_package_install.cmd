@rem installs one package of the python
@rem command line is python path + package name
@echo off
set ppath=%1
set pack=%2
@%ppath%\pip install %pack% > nul 2>&1 
if "%errorlevel%" == "0" (
powershell Write-Host "%pack% installed" -Foreground Green 
) else (
  powershell Write-Host "%pack% install Failed"  -Foreground Red
)
