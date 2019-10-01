@echo off
set lwa=check_mk_agent
set wnx=checkmkservice
powershell Write-Host "'New' Agent Service stopping..." -Foreground Cyan
net stop %wnx% 2> nul > nul
if "%errorlevel%" == "2" powershell Write-Host "'New' Agent Service already stopped" -Foreground Green && goto next
if not "%errorlevel%" == "0" powershell Write-Host "Failed Stop 'NEW' Agent Service" -Foreground Yellow
:next
sc config "%wnx%" start= disabled > nul
if not "%errorlevel%" == "0"  powershell Write-Host "Failed Disable 'NEW' Agent Service, Error=[%errorlevel%]" -Foreground Yellow
sc config "%lwa%" start= auto > nul
if not "%errorlevel%" == "0"  powershell Write-Host "Failed Enable 'LEGACY' Agent Service, Error=[%errorlevel%]" -Foreground Yellow
powershell Write-Host "'Legacy' Agent Service starting..." -Foreground Cyan
net start %lwa% 2> nul > nul
if "%errorlevel%" == "2"  powershell Write-Host "'Legacy' Agent Service already started" -Foreground Green && set errorlevel=0 && goto end
if not "%errorlevel%" == "0"  powershell Write-Host "Failed Start 'Legacy' Agent Service, Error=[%errorlevel%]" -Foreground Red && exit /b 1
powershell Write-Host "'Legacy' Agent Service started successfully" -Foreground Green
:end