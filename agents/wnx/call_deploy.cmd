@echo off
@echo Starting deployment
if "%1" == "SIMULATE_OK" powershell Write-Host "Deploy: SUCCESS" -Foreground Green  && exit 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Deploy: FAIL" -Foreground Red && del %REMOTE_MACHINE%\check_mk_service.msi && exit 99
