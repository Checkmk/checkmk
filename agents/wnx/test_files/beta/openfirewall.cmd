@echo off
set port=6556
if not "%1" == ""  set port=%1
netsh advfirewall firewall delete rule name="CheckMK Windows Agent IN" > nul
netsh advfirewall firewall add rule name="CheckMK Windows Agent IN" description="check_mk new windows agent incoming rule" dir=in localport=%port% protocol=tcp action=allow program="%ProgramFiles(x86)%\check_mk_service\check_mk_agent.exe" profile=private,domain,public enable=yes > nul
if %errorlevel% == 0 powershell Write-Host Firewall opened port '%port%' for New Windows Agent -Foreground Green & exit /B 0
powershell Write-Host Firewall failed to open port '%port%' for New Windows Agent -Foreground Yellow
