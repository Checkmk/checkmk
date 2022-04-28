:: Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
:: This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
:: conditions defined in the file COPYING, which is part of this source code package.

:: Script for Python to build module with caching in remote Directory
:: rebuild is based on the git hash
:: If required file exists in cache, then the file will be copied to the artifact folder
:: otherwise file will be build, uploaded to cache and copied to artifact folder
:: Name format 'python-<version>.<subversion>_<hash>_<id>.cab
:: where <hash> is pretty formatted output from git log .
::       <id> is fixed number(BUILD_NUM)
::       <version> is either 3.4 or 3.9
::       <subversion> is any digit

@echo off
SETLOCAL EnableExtensions EnableDelayedExpansion

if "%3"=="" powershell "Invalid parameters - url should be defined" && exit /B 9
if "%4"=="" powershell "Invalid parameters - version should be defined" && exit /B 10
if "%5"=="" powershell "Invalid parameters - subversion should be defined" && exit /B 10
echo run: %0 %1 %2 %3 %4 %5

:: Increase the value in file BUILD_NUM to rebuild master
set /p BUILD_NUM=<BUILD_NUM

powershell Write-Host "Starting cached build with BUILD_NUM=%BUILD_NUM%..." -foreground Cyan
where curl.exe > nul 2>&1 ||  powershell Write-Host "[-] curl not found"  -Foreground red && exit /B 10
powershell Write-Host "[+] curl found" -Foreground green

set arti_dir=%1
set creds=%2
set url=%3
set version=%4
set subversion=%5

powershell Write-Host "Used URL is `'%url%`'"  -Foreground cyan
if not exist %arti_dir% powershell Write-Host "Directory `'%arti_dir%`' doesn`'t exist" -Foreground red && exit /B 12


:: get hash of the git commit in windows manner
for /f "tokens=*" %%a in ('git log --pretty^=format:^'%%h^' -n 1 .') do set git_hash=%%a
:: verify that git hash is not empty: may happen, that build is performed without checkout
:: we have to build the target in any case and we will use predefined hash
if "%git_hash%" == "" Powershell Write-Host "Git directory is ABSENT. Using PREDEFINED NAME latest as Hash" -Foreground yellow && set git_hash='latest'

rem remove quotes from the result
set git_hash=%git_hash:'=%

set fname=python-%version%.%subversion%_%git_hash%_%BUILD_NUM%.cab
powershell Write-Host "----------------------------------------------"  -Foreground cyan
powershell Write-Host "REAL BUILD IS DISABLED: THIS IS TEMPORARY     "  -Foreground cyan
powershell Write-Host "----------------------------------------------"  -Foreground cyan
if "%version%"=="3.9" set fname=python-3.9.10_dd16e89d8e_16.cab
set artifact_name=%arti_dir%\python-3.cab
if "%version%" == "3.4" (
set artifact_name=%arti_dir%\python-3.4.cab
) else (
set artifact_name=%arti_dir%\python-3.cab
)
echo Used artifact: %artifact_name%
powershell Write-Host "Downloading %fname% from cache..." -Foreground cyan
curl -sSf --user %creds% -o %fname%  %url%/%fname% > nul 2>&1
IF /I "!ERRORLEVEL!" NEQ "0" (
  powershell Write-Host "%fname% not found on %url%, building python %version%.%subversion% ..." -Foreground cyan
  
  :: BUILDING
  if "%version%" == "3.4" (
    make python_344 PY_VER=3.4 PY_SUBVER=4 ||  powershell Write-Host "[-] make failed"  -Foreground red && exit /B 33
  ) else (
    make build PY_VER=%version% PY_SUBVER=%subversion% ||  powershell Write-Host "[-] make failed"  -Foreground red && exit /B 34
  )

 
  echo "Checking the result of the build..."
  if NOT exist %artifact_name% (
    echo "The file %artifact_name% absent, build failed"
    exit /B 14
  )
  powershell Write-Host "Build successful" -Foreground green

  :: UPLOADING to the Nexus Cache:
  echo Uploading to cache %artifact_name% ... %fname% ...
  copy %artifact_name% %fname%

  powershell Write-Host "To be executed: curl -sSf --user creds --upload-file %fname% %url%" -foreground white
  curl -sSf --user %creds% --upload-file %fname% %url%
  IF /I "!ERRORLEVEL!" NEQ "0" (
    del %fname% > nul 
    powershell Write-Host "[-] Failed to upload" -Foreground red
    exit /B 35
  ) else (
    del %fname% > nul 
    powershell Write-Host "[+] Uploaded successfully" -Foreground green
    exit /B 0
  )
) else (
  :: Most probable case. We have the python cab in the cache, just copy cached file to the artifact folder
  powershell Write-Host "The file exists in cache. Moving cached file to artifact" -Foreground green 
  move /Y %fname% %artifact_name%
  powershell Write-Host "[+] Downloaded successfully" -Foreground green
  exit /b 0
)
