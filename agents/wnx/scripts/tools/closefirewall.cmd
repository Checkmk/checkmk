@echo off
set port=6556
if not "%1" == ""  set port=%1
netsh advfirewall firewall delete rule name="CheckMK Windows Agent IN" > nul
if %errorlevel% == 0 powershell Write-Host Firewall closed New Windows Agent -Foreground Green & exit /B 0
