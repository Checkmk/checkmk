::
@echo off 
echo starting with param "%1"
set p=%1
if "%p%"=="" set p=all
if "%p%"=="regression" call scripts\call_regression_tests.cmd && powershell write-Host "SUCCESS!" -Foreground Green &&  exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 19 
if "%p%"=="base" call scripts\call_integration_tests.cmd && powershell write-Host "SUCCESS!" -Foreground Green && exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 20 
if "%p%"=="all" call scripts\call_regression_tests.cmd && call scripts\call_integration_tests.cmd && powershell write-Host "SUCCESS!" -Foreground Green && exit /b 0  ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 20 
