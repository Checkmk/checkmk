@echo off
set work_dir=%cd%
set out_dir=%cd%\tmp\out
set p_name=cpython-3.8
powershell Write-Host "Making temporary folder" -foreground Green
mkdir tmp\out 2> nul
if not exist tmp Write-Host "Failed find tmp folder" -Foreground Red && exit /b 1
if not exist tmp\out Write-Host "Failed find out folder" -Foreground Red && exit /b 1
set build_msi=python\%p_name%\Tools\msi
powershell Write-Host "Entering %build_msi% folder" -foreground Green
cd %build_msi% 2> nul  || powershell Write-Host "cannot find a python sources" -foreground Red && exit /b 2
powershell Write-Host "Starting build" -foreground Green
call buildrelease.bat  -o %out_dir% -b -x86 --skip-nuget --skip-pgo --skip-zip
cd %worK-dir%
