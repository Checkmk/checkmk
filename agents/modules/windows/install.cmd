@echo off
set p_full_name=python-3.8.1
set work_dir=%cd%
set build_dir=%cd%\tmp\out
set pexe=%build_dir%\win32\%p_full_name%.exe
set install_dir=%cd%\tmp\to_install
powershell Write-Host "Installing Python ..." -foreground Cyan 
if exist %install_dir% powershell Write-Host "Python folder exists - removing it" -foreground Cyan && %pexe% /quiet /uninstall && rmdir /q/s %install_dir%
pause
%pexe% /quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_doc=0 Include_dev=0 InstallLauncherAllUsers=0 Include_tcltk=0 Shortcuts=0 AssociateFiles=0 TargetDir=%install_dir%
if not %errorlevel% == 0 powershell Write-Host "Can not install python" -foreground Red && exit /b 2
powershell Write-Host "Python installed" -foreground Green

