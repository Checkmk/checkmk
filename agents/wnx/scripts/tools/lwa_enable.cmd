@echo off
setlocal enabledelayedexpansion enableextensions
set lwa=check_mk_agent
set wnx=checkmkservice
net session 2> nul > nul
if %errorlevel% NEQ 0 powershell Write-Host "Administrative Rights are required to run this Script" -Foreground Red && exit /B 1
powershell Write-Host "'New' Agent Service stopping..." -Foreground Cyan

sc stop %wnx% > nul ||  set e=!errorlevel! && powershell Write-Host "Cant Stop 'New' Agent Service [!e!]" -Foreground Yellow
sc config "%wnx%" start= disabled > nul || set e=!errorlevel! && powershell Write-Host "Cant Disable 'New' Agent Service [!e!]" -Foreground Yellow
sc config "%lwa%" start= auto > nul ||  set e=!errorlevel! &&  powershell Write-Host "Cant Enable 'Legacy' Agent Service [!e!]" -Foreground Yellow

powershell Write-Host "'Legacy' Agent Service starting..." -Foreground Cyan
sc query %lwa% | find "RUNNING" > nul  && powershell Write-Host "'Legacy' Agent Service already running" -Foreground Green  && exit /B 0
sc start %lwa% > nul ||  set e=!errorlevel! && powershell Write-Host "Cant Start 'Legacy' Agent Service [!e!]" -Foreground Yellow && exit /B 1
powershell Write-Host "'Legacy' Agent Service started successfully" -Foreground Green
:end