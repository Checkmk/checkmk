@echo off
setlocal ENABLEDELAYEDEXPANSION
sc query checkmkservice 2> nul > nul
if !errorlevel! NEQ 1060 ( 
    powershell Write-Host Please, uninstall New Windows Agent before cleaning folders -Foreground Cyan
    exit /B 0
)

powershell Write-Host New Windows Agent is not installed and you can clean agents folders safely -Foreground Green
CHOICE.exe /M "Remove Windows Agent folders(this is safe) ?"
if !errorlevel! == 1 (
       DEL /F/Q/S "%ProgramData%\CheckMk\Agent\*.*" > nul
       DEL /F/Q/S  "%ProgramFiles(x86)%\check_mk_service" > nul
       powershell Write-Host Done... -Foreground Green
)
