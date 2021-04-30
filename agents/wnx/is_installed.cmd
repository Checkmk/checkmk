:: Check for installation of the MSI in artefacts
:: Location of the
::
:: 2021 (c) tribe29

@echo off
if "%1" == "" powershell Write-Host "Usage: is_installed.cmd path\to\msi" -Foreground Red && exit /b 5
if not exist "%1" powershell Write-Host "File %1% does not exist" -Foreground Red && exit /b 2

set msi=%1
set theValue=
for /f "delims=" %%a in ('powershell -ExecutionPolicy ByPass -File findagentmsi.ps1') do @set theValue=%%a
if not exist "%theValue%" powershell Write-Host "Agent not found" -foreground Red && exit /b 3
fc /b "%msi%" "%theValue%" >nul && exit /b 0
powershell Write-Host "Agent is not the same, %theValue%" -foreground Red && exit /b 4
