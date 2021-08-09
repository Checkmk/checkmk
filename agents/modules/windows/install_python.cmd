::  Python installer script
::  May be called only from exec_cmd.bat

@echo off
if not defined pexe powershell Write-Host "Must be called from the exec_cmd.bat, pexe" -foreground Red && exit /b 3
if not defined pexe_uninstall powershell Write-Host "Must be called from the exec_cmd.bat, pexe_uninstall" -foreground Red && exit /b 3
if not defined install_dir powershell Write-Host "Must be called from the exec_cmd.bat, install_dir" -foreground Red && exit /b 3
if not defined uninstall_dir powershell Write-Host "Must be called from the exec_cmd.bat, uninstall_dir" -foreground Red && exit /b 3
if not exist %pexe% powershell Write-Host "%pexe% doesnt exist" -foreground Red && exit /b 3

powershell Write-Host "Installing Python ..." -foreground Cyan 
mkdir %uninstall_dir% 2> nul
copy /y %pexe%  %pexe_uninstall% > nul

if not exist %pexe_uninstall% powershell Write-Host "Can not backup installation" -foreground Red && exit /b 2
%pexe% /quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_doc=0 Include_dev=1 InstallLauncherAllUsers=0 Include_tcltk=0 Shortcuts=0 AssociateFiles=0 TargetDir=%install_dir%

if not exist %install_dir%\python.exe powershell Write-Host "Can not install python" -foreground Red && exit /b 2
powershell Write-Host "Python installed, checking pip..." -foreground Cyan
cd %install_dir%

if exist .\Scripts\pip3.exe powershell Write-Host "Python and Pip installed" -foreground Green && exit /b 0
powershell Write-Host "Installing pip..." -foreground Cyan
.\python.exe  -m ensurepip

if not exist .\Scripts\pip3.exe powershell Write-Host "Pip installation failed" -foreground Red && exit /b 7
powershell Write-Host "Python and Pip installed" -foreground Green
exit /b 0

