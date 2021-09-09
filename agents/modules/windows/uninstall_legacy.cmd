:: Uninstall legacy Python using omd/packages/Python/windows/python-3.4.4.msi
:: May be called only from exec_cmd.bat
@echo off

:: not mandatory but simplify the life after changes in toolchain/packages
if not defined install_dir powershell Write-Host "Must be called from the exec_cmd.bat, install_dir" -foreground Red && exit /b 3
if not defined legacy_msi powershell Write-Host "Must be called from the exec_cmd.bat, legacy_msi" -foreground Red && exit /b 4
if not exist %legacy_msi% powershell Write-Host "%legacy_msi% is absent" -foreground Red && exit /b 5

:: UNINSTALL
powershell Write-Host "Uninstalling Legacy Python. If Python was installed, then few minutes are required..." -foreground Cyan 
msiexec /x %legacy_msi% /quiet

:: CLEANUP of remains
if exist "tmp\3.4\to_install" powershell Write-Host "cleaning to_install folder" -foreground white &&  powershell Remove-Item "tmp\3.4\to_install\*" -Force -Recurse

exit /b 0
