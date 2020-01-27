@rem Pip Upgrading script
@rem May be called only from exec_cmd.bat

@rem echo on
if not defined pexe_uninstall powershell Write-Host "This script must be called with exec_cmd.bat" -foreground Red && exit /b 5
powershell Write-Host "Uninstalling Python ..." -foreground Cyan 
if not exist %pexe_uninstall% powershell Write-Host "Python was not correctly installed" -foreground Green && exit /b 0
%pexe_uninstall% /uninstall /quiet
powershell Write-Host "Python uninstalled" -foreground Green

