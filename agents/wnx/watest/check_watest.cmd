rem @echo off
if exist %REMOTE_MACHINE% goto copy
powershell Write-Host %REMOTE_MACHINE% is ABSENT -Foreground Red
exit /b 2
:copy
rem if exist %REMOTE_MACHINE%\ProgramData goto copy2
rem powershell Write-Host Preparing ProgramData -Foreground Green
powershell Write-Host Preparing ProgramData -Foreground Green
pushd ..
call prepare_to_tests.cmd %REMOTE_MACHINE%
popd
