@rem
@rem MAIN WINDOWS SETUP SCRIPT
@rem To get required software installed 
@rem may be called directly by user or indirectly by make
@rem
@rem "git", "far", "visual studio build tools", "wixtoolset"
@echo off
SETLOCAL EnableDelayedExpansion
set error=0

rem Visual Studio Code
set pkg=vscode
set version=
set option=
call :process

rem Pycharm Community
set pkg=pycharm-community
set version=
set option=
call :process

rem Notepad++
set pkg=notepadplusplus
set version=
set option=
call :process


rem Windows Terminal
set pkg=microsoft-windows-terminal
set version=
set option=--pre
call :process


goto eof
:process
powershell Write-Host "Installing '%pkg%'..." -Foreground White
if NOT "!text!" == "" powershell Write-Host "!text!" -Foreground Gray
choco install %pkg% !version! !option! -y -r >nul
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
setx OPENSSL_DIR "C:\Program Files\OpenSSL-Win64"
:eof
if %error% == 1 powershell Write-Host "Installation failed" -Foreground Red && exit /b 1
exit /b 0
