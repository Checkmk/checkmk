@echo off
rem Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
rem This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
rem conditions defined in the file COPYING, which is part of this source code package.
rem
rem Builds the LibreHardwareMonitor based OpenHardwareMonitorCLI into .\dist:
rem   OpenHardwareMonitorCLI.exe  - the CLI, all dependencies except LHM embedded
rem   OpenHardwareMonitorLib.dll  - LibreHardwareMonitorLib.dll, renamed for the bakery
rem
rem Usage: build.cmd [LibreHardwareMonitor commit, tag or branch]
rem Requirements: git, .NET 10 SDK (winget install Microsoft.DotNet.SDK.10)

setlocal
cd /d "%~dp0"

rem Last LibreHardwareMonitor commit tested on real hardware (2026-10-28)
set "LHM_REF=%~1"
if "%LHM_REF%"=="" set "LHM_REF=71040ce2083ecde1f8471acd740a5f1d599744f7"
set "LHM_DIR=%~dp0external\LibreHardwareMonitor"

where git >nul 2>nul || (echo git is required & exit /b 1)
where dotnet >nul 2>nul || (echo .NET 10 SDK is required: winget install Microsoft.DotNet.SDK.10 & exit /b 1)

if not exist "%LHM_DIR%\.git" (
    git init -q "%LHM_DIR%" || exit /b 1
    git -C "%LHM_DIR%" remote add origin https://github.com/LibreHardwareMonitor/LibreHardwareMonitor.git || exit /b 1
)
echo Fetching LibreHardwareMonitor %LHM_REF% ...
git -C "%LHM_DIR%" fetch -q --depth 1 origin %LHM_REF% || exit /b 1
git -C "%LHM_DIR%" checkout -q --force FETCH_HEAD || exit /b 1
git -C "%LHM_DIR%" clean -q -fdx || exit /b 1

dotnet build "%~dp0OpenHardwareMonitorCLI\OpenHardwareMonitorCLI.csproj" -c Release -p:LhmSource=repo "-p:LhmRepoDir=%LHM_DIR%" || exit /b 1

echo.
echo Done. Files for the agent are in %~dp0dist
endlocal
