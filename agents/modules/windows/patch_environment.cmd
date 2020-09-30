@rem  Python installer script
@rem  May be called only from exec_cmd.bat

rem @echo off
if not defined save_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %save_dir% powershell Write-Host "`'%save_dir%`' absent" -foreground red && exit /b 4
cd %save_dir%
copy /Y ..\..\pyvenv.cfg .venv\pyvenv.cfg
copy /Y ..\..\postinstall.cmd .\postinstall.cmd
