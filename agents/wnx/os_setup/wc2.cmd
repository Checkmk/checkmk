@rem
@rem MAIN WINDOWS SETUP SCRIPT
@rem To get required software installed 
@rem may be called directly by user or indirectly by make
@rem
@rem "git", "far", "visual studio build tools", "wixtoolset"
@echo off
SETLOCAL EnableDelayedExpansion
set error=0

rem git, version is latest
set pkg=git.install
set version=
call :process

rem far, version is latest
set pkg=far
set version=
call :process

rem 2019 visual studio build tools, version is latest
set pkg=visualstudio2019buildtools
set version=
call :process

rem 2019 visual studio build tools, version is latest
set pkg=wixtoolset
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




