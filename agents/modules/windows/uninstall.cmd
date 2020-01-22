@echo off
set p_full_name=python-3.8.1
set work_dir=%cd%
set build_dir=%cd%\tmp\out
set pexe=%build_dir%\win32\%p_full_name%.exe
set install_dir=%cd%\tmp\to_install
powershell Write-Host "Uninstalling Python ..." -foreground Cyan 
%pexe% /uninstall /quiet
powershell Write-Host "Python uninstalled" -foreground Green

