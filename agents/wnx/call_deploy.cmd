@echo off
powershell Write-Host Starting deployment -Foreground Green
if "%1" == "SIMULATE_OK" powershell Write-Host "Deploy: SUCCESS" -Foreground Green  && exit 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Deploy: FAIL" -Foreground Red && del %REMOTE_MACHINE%\check_mk_service.msi && exit 99
set root=%cd%\..\..\artefacts
set REMOTE_MACHINE=%root%
@set svc=CheckMkService
set p="%ProgramFiles(X86)%\check_mk_service\upgrade.protocol"
pushd 
cd %root%
powershell Write-Host  "%svc% is cleaning up" -Foreground DarkGray
msiexec /uninstall check_mk_service.msi /quiet /LV* log.tmp
del %p% 2> null
powershell Write-Host  "%svc% is installing" -Foreground Cyan
msiexec /I check_mk_service.msi /quiet /LV* log
powershell Write-Host  "%svc% is installed" -Foreground Green
powershell Start-Sleep 2
@set status=1
powershell Write-Host  "checking status" -Foreground Cyan
sc query "%svc%" | find /i "RUNNING" > null
if %ERRORLEVEL% == 0 goto work
powershell Write-Host  "%svc% is NOT running" -Foreground Red
set status=3
goto end
:work
powershell Write-Host  "%svc% is running" -Foreground Green
if not exist %p% powershell Write-Host "Upgrade Protocol file not found" -Foreground Red && set status=5 && goto end
powershell Write-Host  "protocol file is found" -Foreground Green
powershell Write-Host "%svc% is uninstalling" -Foreground Cyan
msiexec /uninstall check_mk_service.msi /quiet /LV* log.tmp
sc query "%svc%1" > null
if %ERRORLEVEL% == 0 powershell Write-Host "Cannot Uninstall Service" -Foreground Red && set status=5 && goto end
powershell Write-Host  "%svc% is uninstalled" -Foreground Green
set status=0
:end
popd
del %p%
exit /B %status%
