@echo off
if not defined build_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
powershell Write-Host "Making build folder" -foreground Green
mkdir %build_dir% 2> nul
if not exist %build_dir% Write-Host "Failed find tmp folder %build_dir%" -Foreground Red && exit /b 1
set build_msi=python\%p_name%\Tools\msi
powershell Write-Host "Entering %build_msi% folder" -foreground Green
cd %build_msi% 2> nul  || powershell Write-Host "cannot find a python sources" -foreground Red && exit /b 2
powershell Write-Host "Starting build" -foreground Green

call buildrelease.bat  -o %build_dir% -b -x86 --skip-nuget --skip-pgo --skip-zip

