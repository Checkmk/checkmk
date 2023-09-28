:: Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
:: This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
:: conditions defined in the file COPYING, which is part of this source code package.

:: Script to build Open Hardware Monitor
:: 
@echo off
if "%msbuild%" == "" set msbuild=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe
if not exist "%msbuild%" powershell Write-Host "Install Visual Studio 2022, please" -Foreground Red && exit /b 8

make install_extlibs

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
set all_dir=%cur_dir%\build\ohm\

powershell Write-Host "Building OHM using %msbuild%" -Foreground White
"%msbuild%" .\ohm\ohm.sln /p:OutDir=%all_dir%;TargetFrameworkVersion=v4.6;Configuration=Release
if not %errorlevel% == 0 powershell Write-Host "Failed Build" -Foreground Red && exit /b 14
:: copy %build_dir%\ohm_host.exe %arte%\ /y || powershell Write-Host "Failed to copy ohm_host.exe" -Foreground Red && exit /b 33
:: copy %build_dir%\ohm_bridge.dll %arte%\ /Y || powershell Write-Host "Failed to copy ohm_host.exe" -Foreground Red && exit /b 35
copy %all_dir%\OpenHardwareMonitorLib.dll %arte%\ /Y || powershell Write-Host "Failed to copy OpenHardwareMonitorLib.dll" -Foreground Red && exit /b 34
copy %all_dir%\OpenHardwareMonitorCLI.exe %arte%\ /Y || powershell Write-Host "Failed to copy OpenHardwareMonitorCLI.exe" -Foreground Red && exit /b 35
