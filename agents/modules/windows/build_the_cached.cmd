@rem Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
@rem This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
@rem conditions defined in the file COPYING, which is part of this source code package.

@rem Script for Python to build module with caching in remote Directory
@rem rebuild is based on the git hash
@rem If required file exists in cache, then the file will be copied to the artifact folder
@rem otherwise file will be build, uploaded to cache and copied to artifact folder
@rem Name format 'python-3.8_<hash>_<id>.zip
@rem where <hash> is pretty formatted output from git log .
@rem       <id> is fixed number(BUILD_NUM)

@echo off
SETLOCAL EnableExtensions EnableDelayedExpansion

@if "%3"=="" powershell 'Invalid parameters' && exit /B 9

rem Increase the value in file BUILD_NUM to rebuild master
set /p BUILD_NUM=<BUILD_NUM

powershell Write-Host "Starting cached build with BUILD_NUM=%BUILD_NUM%..." -foreground Cyan
where curl.exe > nul 2>&1 ||  powershell Write-Host "[-] curl not found"  -Foreground red && exit /B 10
powershell Write-Host "[+] curl found" -Foreground green

set arti_dir=%1
set creds=%2
set url=%3
@powershell Write-Host "Used URL is `'%url%`'"  -Foreground cyan
if not exist %arti_dir% powershell Write-Host "Directory `'%arti_dir%`' doesn`'t exist" -Foreground red && exit /B 12


rem get hash of the git commit in windows manner
for /f "tokens=*" %%a in ('git log --pretty^=format:^'%%h^' -n 1 .') do set git_hash=%%a
rem verify that git hash is not empty: may happen, that build is performed without checkout
rem we have to build the target in any case and we will use predefined hash
if "%git_hash%" == "" Powershell Write-Host "Git directory is ABSENT. Using PREDEFINED NAME latest as Hash" -Foreground yellow && set git_hash='latest'

rem remove quotes from the result
set git_hash=%git_hash:'=%

set fname=python-3.8_%git_hash%_%BUILD_NUM%.zip
powershell Write-Host "Downloading %fname% from cache..." -Foreground cyan
curl -sSf --user %creds% -o %fname%  %url%/%fname% > nul 2>&1
IF /I "!ERRORLEVEL!" NEQ "0" (
  powershell Write-Host "%fname% not found on %url%, building..." -Foreground cyan
  rem making:
  make ||  powershell Write-Host "[-] make failed"  -Foreground red && exit /B 33

  powershell Write-Host "Checking the result of the build..." -Foreground cyan
  if NOT exist %arti_dir%\python-3.8.zip (
    powershell -Write-Host "The file absent, build failed" -Foreground red
    exit /B 14
  )
  powershell Write-Host "Build successful" -Foreground green

  rem Download to the Nexus Cache:
  powershell Write-Host "Uploading to cache..." -Foreground cyan
  copy %arti_dir%\python-3.8.zip %fname%

  @echo "Command line: curl -sSf --user creds --upload-file %fname% %url%"
  curl -sSf --user %creds% --upload-file %fname% %url%
  IF /I "!ERRORLEVEL!" NEQ "0" (
    del %fname% > nul 
    powershell Write-Host "[-] Failed to upload" -Foreground red
    exit /B 35
  ) else (
    del %fname% > nul 
    powershell Write-Host "[+] Finished successfully" -Foreground green
    exit /B 0
  )
) else (
  rem Most probable case, just copy cached file to the artifact folder
  powershell Write-Host "The file exists in cache. Moving cached file to artifact" -Foreground green 
  move /Y %fname% %arti_dir%/%python-3.8.zip
  powershell Write-Host "[+] Finished successfully" -Foreground green
  exit /b 0
)
