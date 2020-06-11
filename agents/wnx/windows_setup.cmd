@rem
@rem MAIN WINDOWS SETUP SCRIPT
@rem To get required software installed 
@rem may be called directly by user or indirectly by make
@rem
@rem "python2.7.16", "upx", "make", "rsync"
@echo off
SETLOCAL EnableDelayedExpansion
set error=0

rem python, version is required
set pkg=python2 
set version=--version 2.7.16
call :process

rem make, version is latest
set pkg=make
set version=
call :process

rem upx, version is latest
set pkg=upx
set version=
call :process

rem rsync, version is latest
set pkg=rsync
set version=
call :process

rem grep, version is latest
set pkg=grep
set version=
call :process

rem diff, version is latest
set pkg=diffutils
set version=
call :process

rem 7zip, version is latest
set pkg=7zip
set version=
call :process

goto eof
:process
@echo @choco install %pkg% !version! -y -r > nul 2>&1
@choco install %pkg% !version! -y -r >nul
if "%errorlevel%" == "0" (
powershell Write-Host "'%pkg% '" -Foreground White  -nonewline
powershell Write-Host " is installed" -Foreground Green
exit /b
) else (
powershell Write-Host "'%pkg% '"  -Foreground White -nonewline
powershell Write-Host " is FAILED to install" -Foreground Red
set error=1
exit /b
)
:eof
if %error% == 1 powershell Write-Host "Installation failed" -Foreground Red && exit /b 1
exit /b 0




