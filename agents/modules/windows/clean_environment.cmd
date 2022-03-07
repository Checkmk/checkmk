:: The script makes some changes in the envirionment
:: * replaces hard links using zip unzip
:: * removes a lot of not required files

@echo off

if not defined save_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 12
if not exist %save_dir% powershell Write-Host "`'%save_dir%`' absent" -foreground red && exit /b 14
set str1=%save_dir%
if x%str1:tmp=%==x%str1% powershell Write-Host "Looks as BAD path" -Foreground red && exit /b 17
cd %save_dir% || Powershell Write-Host "`'%save_dir%`' absent" -Foreground red && exit /b 15
powershell Write-Host "Cleaning environment" -foreground Cyan
powershell Write-Host "Rezip to avoid remove symbolic links" -foreground white
7z a -r -tzip -y -mmt4 ar .venv
7z x -y ar.zip
del /Q ar.zip

:: root files 
powershell Write-Host "Cleaning environment phase 1" -foreground Cyan
powershell Write-Host "zips" -foreground white
del /Q python-3.8.zip
del /Q python-3.4.zip
powershell Write-Host "root files" -foreground white
del /Q *.*
powershell Write-Host "root folders" -foreground white
rd /q /s libs
rd /q /s tools
rd /q /s include
rd /q /s DLLs
rd /q /s scripts
powershell Write-Host "pycaches" -foreground white
del /Q Lib\__pycache__\*.*

powershell Write-Host "Lib" -foreground white
rd /Q /S Lib\venv
rd /Q /S Lib\unittest
rd /Q /S Lib\test
powershell Write-Host "tcl" -foreground white
rd /Q /S .venv\Lib\tcl8.6

powershell Write-Host "other files" -foreground white
del /Q .venv\.project
del /Q Lib\turtle.py
del /Q .venv\Lib\site-packages\PyWin32.chm
:: On a request from LM/Clients
del /Q .venv\Scripts\pythonw.exe 
powershell Write-Host "pip, pipenv, virtualenv" -foreground white
for /f %%i in ('dir /a:d /s /b pipenv*') do rd /s /q %%i
for /f %%i in ('dir /a:d /s /b virtualenv*') do rd /s /q %%i

powershell Write-Host "Cleaning environment phase 2" -foreground Cyan
:: Agressive cleaning phase
:: __pycache__ as not required
for /f %%i in ('dir /a:d /s /b __pycache__') do del /Q "%%i\*.*"

:: lib2to3 as not required
powershell Write-Host "lib2to3" -foreground white
rd /Q /S Lib\lib2to3

:: ensurepip as not required
powershell Write-Host "ensurepips" -foreground white
rd /Q /S Lib\ensurepip

:: Lib\site-packages\setuptools as duplicated in .venv
cd Lib
powershell Write-Host "setuptools" -foreground white
for /f %%i in ('dir /a:d /s /b setuptools*') do rd /s /q %%i
cd ..

exit /b 0