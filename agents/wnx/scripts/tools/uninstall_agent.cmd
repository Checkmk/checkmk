@echo off
rem **************************************************************************************
rem This is small tool to remove Windows Agent from the command line
rem USE CAREFULLY, because all your files in the "%ProgramData%\CheckMK\Agent" will be deleted
rem This tool can optionally remove logs and ugrade.protocol
rem We are using sc to find Check MK Service instead of wmic, because 'wmic' is very very slow
rem **************************************************************************************
rem uninstall_agent.cmd with yes parameter uninstall service and remove all files silently
rem uninstall_agent.cmd with all additionally remove service log and upgrade.protocol
rem 
rem Examples:
rem "uninstall_agent all" interactively uninstall service and delete all files except upgrade_protocol and log
rem "uninstall_agent all" interactively uninstall service and delete all files
rem "uninstall_agent yes" silently uninstall service and delete all files except upgrade_protocol and log
rem "uninstall_agent yes all" silently uninstall service and delete all files
rem 
rem **************************************************************************************
@SETLOCAL EnableDelayedExpansion
net session 2> nul > nul
if %errorlevel% NEQ 0 powershell Write-Host "Administrative Rights are required to run this Script" -Foreground Red && exit /B 1


if not "%1" == "yes" if not "%1" == "all"  if not "%1" == "" powershell Write-Host "Usage: uninstall_agent [yes] [all]" -Foreground Yellow && goto exit_all
if not "%2" == "yes" if not "%2" == "all"  if not "%2" == "" powershell Write-Host "Usage: uninstall_agent [yes] [all]" -Foreground Yellow && goto exit_all
if "%1" == "yes" set silent=1
if "%1" == "all" set all=1
if "%2" == "yes" set silent=1
if "%2" == "all" set all=1
if "!silent!"=="1" powershell Write-Host "Uninstalling Check MK Service and removing all files SILENTLY " -Foreground Cyan

rem check service installed
sc query | find /I "checkmkservice" > nul
if not errorlevel 1 powershell Write-Host "Check MK Service is installed" -Foreground Green && goto remove_service
if errorlevel 1 powershell Write-Host "Check MK Service is NOT installed" -Foreground Cyan && goto remove_files

:remove_service
if "!silent!"=="1" goto exec_remove_service
rem GUI:
powershell Write-Host "Do you want to uninstall Check MK Service? [YN] " -Foreground Green
CHOICE /N
if errorlevel 2 goto remove_files

rem remove service
:exec_remove_service
powershell Write-Host "Uninstalling Check MK Service. This is long process: please wait..." -Foreground Cyan
wmic product where name="Check MK Service" call uninstall /nointeractive

:remove_files
if "!silent!"=="1" goto exec_remove_files
rem GUI:
powershell Write-Host "Do you want to remove all Check MK Service Files? [YN] " -Foreground Green
CHOICE /N
if errorlevel 2 goto exit_all

rem remove files
:exec_remove_files
set fldr="%ProgramData%\CheckMK\Agent"
taskkill.exe /F /IM OpenHardwareMonitorCLI.exe
taskkill.exe /F /IM OpenHardwareMonitorCLI.exe
net stop winring0_1_2_0
powershell Write-Host "Deleting folder !fldr!" -Foreground Cyan
DEL /F/Q/S !fldr! > NUL
RMDIR /Q/S !fldr!

if not "!all!" == "1" goto exit_all
powershell Write-Host "Deleting log and protocol upgrade files..." -Foreground Cyan
del %public%\check_mk.log
del "%ProgramFiles(x86)%\check_mk_service\upgrade.protocol"
:exit_all