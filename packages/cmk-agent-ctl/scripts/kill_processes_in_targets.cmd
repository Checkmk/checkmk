@echo off
if "%1" == "" (
echo "First parameter should represent target" -Foreground Red
exit /b 1
)
pushd target\%1 || echo "failed to change dir to target\%1 - nothing to do" && exit /b 0
powershell -ExecutionPolicy ByPass -File ..\..\..\..\..\scripts\windows\kill_all_processes_in_folder.ps1 || echo "failed to find kill script" &&  exit 1
popd