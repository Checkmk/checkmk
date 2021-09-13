:: Install legacy Python from omd/packages/Python/windows/python-3.4.4.msi
:: May be called only from exec_cmd.bat
@echo off

:: Checks are not mandatory but simplify the life after changes in toolchain/packages
if not defined install_dir powershell Write-Host "Must be called from the exec_cmd.bat, install_dir" -foreground Red && exit /b 3
if not defined legacy_msi powershell Write-Host "Must be called from the exec_cmd.bat, legacy_msi" -foreground Red && exit /b 4
if not exist %legacy_msi% powershell Write-Host "%legacy_msi% is absent" -foreground Red && exit /b 5

:: INSTALL
powershell Write-Host "Installing Legacy Python. This may require few minuts..." -foreground Cyan 

:: Some of flags may not work(it is not clear why).
msiexec /i %legacy_msi% /quiet TargetDir=%install_dir% InstallAllUsers=0 Include_test=0 Include_tcltk=0 Shortcuts=0 && powershell Write-Host "done!" -foreground green && exit /b 0

:: Failure
powershell Write-Host "failed" -foreground red 
exit /b 1

