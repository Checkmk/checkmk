@rem Name should be LONG ENOUGH to use 

@echo off
if "%1" == "" powershell Write-Host "no name " && exit /b 0

:LOOP
PSLIST %1 >nul 2>&1
IF ERRORLEVEL 1 (
  GOTO CONTINUE
) ELSE (
  powershell Write-Host "%1 is still running" -foreground Yellow
  TIMEOUT /T 5
  GOTO LOOP
)

:CONTINUE
