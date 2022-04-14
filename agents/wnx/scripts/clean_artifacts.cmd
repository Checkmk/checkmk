@echo off
CALL :NORMALIZEPATH "%arte%"
SET arte=%RETVAL%

if "%arte%" == "" powershell Write-Host "arte not defined" -Foreground Red  && exit /b 1
:: kill file with name of folder if it exists for some reason
if not exist %arte%\ del /Y %arte% 2> nul
:: always make dir
mkdir %arte% 2> nul
del %arte%\check_mk_service.msi 2> nul
del %arte%\check_mk_service_unsigned.msi 2> nul
del %arte%\check_mk_agent.msi 2> nul
del %arte%\check_mk_agent.exe 2> nul
del %arte%\check_mk_agent-64.exe 2> nul
exit /b 0

:: ========== FUNCTIONS ==========
EXIT /B

:NORMALIZEPATH
  SET RETVAL=%~f1
  EXIT /B

