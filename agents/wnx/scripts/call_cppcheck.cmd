@echo off
where cppcheck 2>nul > nul
if errorlevel 1 powershell Write-Host "Install cppcheck, please" -ForegroundColor Red && exit /b 1
where ugrep 2>nul > nul
if errorlevel 1 powershell Write-Host "Install ugrep, please" -ForegroundColor Red && exit /b 1
cppcheck -j6 -D_MT -D_WIN32 -DCMK_SERVICE_NAME -DON_OUT_OF_SCOPE --project=wamain.sln "--project-configuration=Release|x64" --suppressions-list=suppressions.txt . | ugrep -v "Checking." | ugrep -v "files checked"
if errorlevel 2 powershell Write-Host "Failed checkcpp" -ForegroundColor Red && exit /b 2
powershell Write-Host "checkcpp OK" -ForegroundColor Green
exit /b 0
