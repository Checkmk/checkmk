@echo off
setlocal enabledelayedexpansion enableextensions
set lwa=check_mk_agent
set wnx=checkmkservice
net session 2> nul > nul
if %errorlevel% NEQ 0 powershell Write-Host "Administrative Rights are required to run this Script" -Foreground Red && exit /B 1
powershell Write-Host "'Legacy' Agent Service stopping..." -Foreground Cyan

sc stop %lwa% > nul ||  set e=!errorlevel! &&  powershell Write-Host "Cant Stop 'Legacy' Agent Service [!e!]" -Foreground Yellow
sc config %lwa% start= disabled > nul ||  set e=!errorlevel! && powershell Write-Host "Cant Disable 'Legacy' Agent Service [!e!]" -Foreground Yellow
sc config %wnx% start= auto > nul ||  set e=!errorlevel! && powershell Write-Host "Cant Enable 'New' Agent Service [!e!]" -Foreground Yellow

powershell Write-Host "'New' Agent Service starting..." -Foreground Cyan
sc query %wnx% | find "RUNNING" > nul  && powershell Write-Host "'New' Agent Service already running" -Foreground Green  && exit /B 0
sc start %wnx% > nul ||  set e=!errorlevel! && powershell Write-Host "Cant Start 'New' Agent Service [!e!]" -Foreground Yellow && exit /B 1
powershell Write-Host "'New' Agent Service started successfully" -Foreground Green
:end