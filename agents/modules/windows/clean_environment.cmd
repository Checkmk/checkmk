@rem The script makes some changes in the envirionment
@rem * replaces hard links using zip unzip
@rem * removes a lot of not required files

@echo off
if not defined save_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 12
if not exist %save_dir% powershell Write-Host "`'%save_dir%`' absent" -foreground red && exit /b 14
set str1=%save_dir%
if x%str1:tmp=%==x%str1% powershell Write-Host "Looks as BAD path" -Foreground red && exit /b 17
cd %save_dir% || Powershell Write-Host "`'%save_dir%`' absent" -Foreground red && exit /b 15
@powershell Write-Host "Cleaning environment" -foreground Cyan
@7z a -r -tzip -y -mmt4 ar .venv
@7z x -y ar.zip
@del /Q ar.zip
@rem root files 

@powershell Write-Host "Cleaning environment phase 1" -foreground Cyan
@echo off
del /Q python-3.8.zip
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

@powershell Write-Host "Cleaning environment phase 2" -foreground Cyan
@rem Agressive cleaning phase
@rem __pycache__ as not required
for /f %%i in ('dir /a:d /s /b __pycache__') do del /Q "%%i\*.*"
@rem lib2to3 as not required
rd /Q /S Lib\lib2to3
@rem ensurepip as not required
rd /Q /S Lib\ensurepip
@rem Lib\site-packages\setuptools as duplicated in .venv
cd Lib
for /f %%i in ('dir /a:d /s /b setuptools*') do rd /s /q %%i
cd ..
