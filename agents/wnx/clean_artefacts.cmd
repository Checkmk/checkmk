@echo off
if "%arte%" == "" powershell Write-Host "erte not defined" -Foreground Red  && exit /b 1
del %arte%\check_mk_service.msi 2> nul
del %arte%\check_mk_service_unsigned.msi 2> nul
del %arte%\check_mk_agent.msi 2> nul
del %arte%\check_mk_agent.exe 2> nul
del %arte%\check_mk_agent-64.exe 2> nul
