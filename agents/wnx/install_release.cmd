@echo off
:: File to install resulting ms in the windows agent
SETLOCAL EnableDelayedExpansion

set the_msi=..\..\artefacts\check_mk_agent.msi
set the_dir=%ProgramData%\checkmk\agent\update
set the_disappear=%ProgramData%\checkmk\agent\update\check_mk_agent.msi
if not exist %the_msi% powershell Write-Host "%the_msi% is absent, please, build" -foreground red && exit /b 1
if not exist %the_dir% powershell Write-Host "%the_dir% is absent, please, install Windows agent" -foreground red && exit /b 2
powershell Write-Host "Copy %the_msi% into %the_dir% ..." -foreground cyan
copy /Y %the_msi% %the_dir% || powershell Write-Host "Copy failed" -foreground red && exit /b 3
powershell Write-Host "Waiting for install start" -nonewline  -foreground cyan
for /l %%x in (1, 1, 10 ) do (
  if not exist %the_disappear% powershell Write-Host "`nInstallation looks good" -foreground green && exit /b 0
  powershell Start-Sleep 1
  powershell Write-Host "." -nonewline -foreground cyan
)

powershell Write-Host "`nInstallation failed" -foreground red
exit /b 4

