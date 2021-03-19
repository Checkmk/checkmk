@rem
@rem MAIN WINDOWS SETUP SCRIPT
@rem To get required software installed 
@rem
@rem "python2.7.16", "upx", "make"

@echo off
set error=0
set pkg=python2 -version 2.7.16
call :process
set pkg=make
call :process
set pkg=upx
call :process
goto eof
:process
@choco install %pkg% -a > nul 2>&1 
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
if %error% == 1 exit /b 1
exit /b 0




