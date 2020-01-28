@rem  Python installer script
@rem  May be called only from exec_cmd.bat

@rem echo on
if not defined pexe powershell Write-Host "Must be called from the exec_cmd.bat, pexe" -foreground Red && exit /b 3
if not defined pexe_uninstall powershell Write-Host "Must be called from the exec_cmd.bat, pexe_uninstall" -foreground Red && exit /b 3
if not defined install_dir powershell Write-Host "Must be called from the exec_cmd.bat, install_dir" -foreground Red && exit /b 3
if not defined uninstall_dir powershell Write-Host "Must be called from the exec_cmd.bat, uninstall_dir" -foreground Red && exit /b 3
if not exist %pexe% powershell Write-Host "%pexe% doesnt exist" -foreground Red && exit /b 3
powershell Write-Host "Installing Python ..." -foreground Cyan 
mkdir %uninstall_dir% 2> nul
copy /y %pexe%  %pexe_uninstall% > nul
if not exist %pexe_uninstall% powershell Write-Host "Can not backup installation" -foreground Red && exit /b 2
@rem psexec el %pexe% /quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_doc=0 Include_dev=1 InstallLauncherAllUsers=0 Include_tcltk=0 Shortcuts=0 AssociateFiles=0 TargetDir=%install_dir%
powershell Start-Process %pexe% -ArgumentList "/quiet, InstallAllUsers=0, Include_launcher=0, Include_test=0, Include_doc=0, Include_dev=1, InstallLauncherAllUsers=0, Include_tcltk=0, Shortcuts=0, AssociateFiles=0, TargetDir=%install_dir%" -verb RunAs -Wait
if not %errorlevel% == 0 del %pexe_uninstall% && powershell Write-Host "Can not install python" -foreground Red && exit /b 2
powershell Write-Host "Python installed" -foreground Green


