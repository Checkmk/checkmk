@echo off
rem **************************************************************************************
rem This small script is used to solve problems with OpenHardwareMonitor section
rem "Administrative Rights" are required
rem **************************************************************************************
rem 1. If openhardwaremonitor section is absent, you may try this solution.
rem 2. The script is relative safe: stops OHM WMI provider and clean WMI data.
rem 3. As additional check you may also try in powershell command 
rem     Get-WmiObject -Namespace "root\OpenHardwareMonitor" -Class Sensor -Impersonation 3
rem    start powershell.exe, copy paste string above and hit Enter.
rem    If output is absent or command is hanging up, then you should try this script
rem **************************************************************************************
rem Do not forget: Your Agent must be configured to provide OpenHardwareMoniotr section
rem **************************************************************************************
net session 2> nul
if %errorlevel% NEQ 0 powershell Write-Host "Administrative Rights are required to run this Script" -Foreground Red && exit /B 1
powershell Write-Host "Stopping Windows Agent and OpenHardwareMonitor..." -Foreground Cyan
net stop check_mk_agent
taskkill.exe /F /IM OpenHardwareMonitorCLI.exe
powershell Write-Host "Cleaning WMI..." -Foreground Cyan
powershell.exe  -command "Get-WmiObject -query \"Select * From __Namespace Where Name='OpenHardwareMonitor'\" -Namespace \"root\" | Remove-WmiObject"
powershell Write-Host "Starting Windows Agent again..." -Foreground Cyan
rem net start check_mk_agent
