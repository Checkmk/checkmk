:: Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
:: This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
:: conditions defined in the file COPYING, which is part of this source code package.

:: Main building script for Python
:: Default come from the Makefile

@echo off
set artefact_dir=..\..\..\artefacts\
@if "%1"=="cached" goto cached
@if "%1"=="build" goto python_build 
powershell Write-Host 'Invalid parameter...' -foreground Red && goto usage

:python_build
powershell Write-Host 'Building python...' -foreground Cyan
if not exist "%artefact_dir%" powershell Write-Host 'Creating directory...' -foreground Cyan && mkdir "%artefact_dir%"
make build
goto exit

:cached
powershell Write-Host 'Delivering cached python...' -foreground Cyan
if not exist "%artefact_dir%" powershell Write-Host 'Creating directory...' -foreground Cyan && mkdir "%artefact_dir%"

:: Determine expected python version using target in Makefile
set tmpFile=python_version_%RANDOM%.tmp
make python_version > %tmpFile%
set /p python_version= < %tmpFile%
del %tmpFile%
@if NOT "%3"=="" ( 
  call build_the_cached.cmd "%artefact_dir%" %2 %3 3.4 4 || powershell Write-Host "Failed python 1" -foreground red && exit /b 11
  call build_the_cached.cmd "%artefact_dir%" %2 %3 %python_version% || powershell Write-Host "Failed python 2" -foreground red && exit /b 12
  powershell Write-Host "Builds are successfull" -foreground green
  make integration || powershell Write-Host "Failed integration" -foreground red && exit /b 13
  goto exit
)
powershell Write-Host 'Invalid parameters' -Foreground Red 
goto usage

:usage
:: we are using powershell to call the executable with admin rights and wait
:: this trick is required to install python in non very interactive environments
:: like jenkins build
@powershell Write-Host "Possible parameters:" -foreground Cyan
@powershell Write-Host "`tcached `<creds`> `<url`>`t- cached build of python" -foreground white
@powershell Write-Host "`tbuild`t`t`t- builds python module" -foreground white && exit /b 9
:exit
