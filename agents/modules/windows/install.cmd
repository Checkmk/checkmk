@echo off
powershell Write-Host "Installing Python ..." -foreground Cyan 
mkdir %uninstall_dir% 2> nul
copy /y %pexe%  %pexe_uninstall% > nul
if not exist %pexe_uninstall% powershell Write-Host "Can not backup installation" -foreground Red && exit /b 2
%pexe% /quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_doc=0 Include_dev=1 InstallLauncherAllUsers=0 Include_tcltk=0 Shortcuts=0 AssociateFiles=0 TargetDir=%install_dir%
if not %errorlevel% == 0 del %pexe_uninstall% && powershell Write-Host "Can not install python" -foreground Red && exit /b 2
powershell Write-Host "Python installed" -foreground Green


