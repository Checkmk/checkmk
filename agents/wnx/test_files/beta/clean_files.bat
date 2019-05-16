@echo off
sc query checkmkservice 2> nul > nul
if not "%errorlevel%" == "1060" ( 
    powershell Write-Host Uninstall New Windows Agent before cleaning -Foreground Cyan
    exit  0
)
powershell Write-Host Windows Agent is not installed your can clean folders safely. -Foreground Green
CHOICE.exe /M "Do you really want to remove folders(this is safe)"
if "%errorlevel%" == "1" (
       DEL /F/Q/S "%ProgramData%\CheckMk\Agent\*.*" > nul
       DEL /F/Q/S  "%ProgramFiles(x86)%\check_mk_service" > nul
       powershell Write-Host Done... -Foreground Green
)
