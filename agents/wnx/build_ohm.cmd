@echo off
:: File to Build ohm distro
::
@echo off
set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
set build_dir=.\build\Bin\release
"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe" .\ohm\ohm.sln /p:Configuration=Release
if not %errorlevel% == 0 powershell Write-Host "Failed Build" -Foreground Red && exit /b 14
copy %build_dir%\ohm_host.exe %arte%\ /y || powershell Write-Host "Failed to copy ohm_host.exe" -Foreground Red && exit /b 33
copy %build_dir%\ohm_bridge.dll %arte%\ /Y || powershell Write-Host "Failed to copy ohm_host.exe" -Foreground Red && exit /b 35
copy %build_dir%\OpenHardwareMonitorLib.dll %arte%\ /Y || powershell Write-Host "Failed to copy OpenHardwareMonitorLib.dll" -Foreground Red && exit /b 34
copy %build_dir%\OpenHardwareMonitorCLI.exe %arte%\ /Y || powershell Write-Host "Failed to copy OpenHardwareMonitorCLI.exe" -Foreground Red && exit /b 34
