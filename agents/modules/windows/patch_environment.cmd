:: Python environemnet patching script.
:: Adds postinstall script and optionally runtime to support 
:: out of the box Mid-age OS, like Windows Server 2012.
:: May be called only from exec_cmd.bat.

rem @echo off
if not defined save_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %save_dir% powershell Write-Host "`'%save_dir%`' absent" -foreground red && exit /b 4

cd %save_dir%
powershell Write-Host "Patching environment" -foreground green
echo home = C:\ProgramData\checkmk\agent\modules\python-3>.venv\pyvenv.cfg
echo version_info = %PY_VER%.%PY_SUBVER%>>.venv\pyvenv.cfg
echo include-system-site-packages = false>>.venv\pyvenv.cfg

:: postinstall
copy /Y %cur_dir%\postinstall.cmd .\postinstall.cmd
if "%PY_VER%" == "3.4" exit /b 0

:: runtime
copy /Y %cur_dir%\runtime\*.dll .venv\Scripts\

exit /b 0
