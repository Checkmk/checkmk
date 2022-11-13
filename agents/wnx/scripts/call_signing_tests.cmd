@echo off
::
:: File to run Signing Tests in the tests/integration folder
:: Should be called after successful build with correct artifacts
::

set cur_dir=%cd%

powershell Write-Host "Windows agent Signing Tests are starting" -Foreground Cyan
set loc_1="C:\Program Files (x86)\Microsoft SDKs\ClickOnce\SignTool\signtool.exe"
set loc_2="C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe"
if exist %loc_1%  (
set l=%loc_1%
) else (
if exist %loc_2% (
set l=%loc_2%
) else (
exit /b 113
)
)
%l% verify /pa ../../artefacts/check_mk_agent.msi || echo "check_mk_agent.msi not signed" && exit /b 1
%l% verify /pa ../../artefacts/OpenHardwareMonitorCLI.exe || echo "OpenHardwareMonitorCLI.exe not signed" && exit /b 1
%l% verify /pa ../../artefacts/OpenHardwareMonitorLIB.dll || echo "OpenHardwareMonitorLib.dll not signed" && exit /b 1
%l% verify /pa ../../artefacts/check_mk_agent.exe || echo "check_mk_agent.exe not signed" && exit /b 1
%l% verify /pa ../../artefacts/check_mk_agent-64.exe || echo "check_mk_agent-64.exe not signed" && exit /b 1
%l% verify /pa ../../artefacts/cmk-agent-ctl.exe || echo "cmk-agent-ctl.msi not signed" && exit /b 1

powershell Write-Host "Windows agent Signing Tests succeeded" -Foreground Green
exit /b 0
