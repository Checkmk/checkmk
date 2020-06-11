@echo off
if not defined save_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %save_dir% powershell Write-Host "`'%save_dir%`' absent" -foreground red && exit /b 4
set str1=%save_dir%
if x%str1:tmp=%==x%str1% powershell Write-Host "Looks as BAD path" -Foreground red && exit /b 7
cd %save_dir% || Powershell Write-Host "`'%save_dir%`' absent" -Foreground red && exit /b 5
@powershell Write-Host "Cleaning environment" -foreground red 
@7z a -r -tzip -y -mmt4 ar .venv
@7z x -y ar.zip
@rm ar.zip
@rem root files 
@echo off
del /Q *.*
rd /q /s libs
rd /q /s tools
rd /q /s include
rd /q /s DLLs
rd /q /s scripts
del /Q Lib\__pycache__\*.*
del /Q .venv\.project
rd /Q /S Lib\venv
rd /Q /S Lib\unittest
del /Q Lib\turtle.py
for /f %%i in ('dir /a:d /s /b pipenv*') do rd /s /q %%i
for /f %%i in ('dir /a:d /s /b virtualenv*') do rd /s /q %%i
for /f %%i in ('dir /a:d /s /b pip*') do rd /s /q %%i

