@rem
@rem MAIN WINDOWS SETUP SCRIPT
@rem To get required software installed 
@rem may be called directly by user or indirectly by make
@rem
@rem "python3", "upx", "make", "rsync", "7zip", "grep", "diffutils" 
@echo off
SETLOCAL EnableDelayedExpansion
set error=0

echo SETUP LONG FILENAME SUPPORT:
powershell Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1

rem python, version is latest
set pkg=python3 
set version=
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
powershell Write-Host "Installing '%pkg%'..." -Foreground White
choco install %pkg% !version! -y -r >nul
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

