@echo off
if "%1%"=="" powershell Write-Host "you need a path" -Foreground Red && exit 1
set np=%1
echo %path%|find /i "%np%">nul  || @echo 'new path %path%;%np%'  && goto set_path
powershell Write-Host "path exists" -Foreground Green
exit 0
:set_path
CHOICE /C YN /M "Press Y for Yes, N for No." 
if %errorlevel%==1 powershell Write-Host "path exists" -Foreground Green && setx path %path%;%np% && exit /b 0
