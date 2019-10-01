@echo off
set lwa=check_mk_agent
set wnx=checkmkservice
powershell Write-Host "'Legacy' Agent Service stopping..." -Foreground Cyan
net stop %lwa% 2> nul > nul
if "%errorlevel%" == "2" powershell Write-Host "'Legacy' Agent Service already stopped" -Foreground Green && goto next
if not "%errorlevel%" == "0" powershell Write-Host "Failed Stop 'Legacy' Agent Service [%errorlevel%]" -Foreground Yellow
:next
sc config "%lwa%" start= disabled > nul
if not "%errorlevel%" == "0"  powershell Write-Host "Failed Disable 'Legacy' Agent Service, Error=[%errorlevel%]" -Foreground Yellow
sc config "%wnx%" start= auto > nul
if not "%errorlevel%" == "0"  powershell Write-Host "Failed Enable 'New' Agent Service, Error=[%errorlevel%]" -Foreground Yellow
powershell Write-Host "'New' Agent Service starting..." -Foreground Cyan
net start %wnx% 2> nul > nul
if "%errorlevel%" == "2"  powershell Write-Host "'New' Agent Service already started" -Foreground Green && set errorlevel=0 && goto end
if not "%errorlevel%" == "0"  powershell Write-Host "Failed Start 'New' Agent Service, Error=[%errorlevel%]" -Foreground Red &&  exit /b 1
powershell Write-Host "'New' Agent Service started successfully" -Foreground Green
:end