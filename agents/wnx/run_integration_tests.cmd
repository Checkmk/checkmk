@echo off
:: To execute all complicated tests of windows agent
:: params regression, mid, mid_ext, mid_ext_long, integration, all
::
:: CI must run regression, mid, integration, all
:: Dev machine must run also mid_ext and mid_ext_long
:: later tests may require some additional package installed which ae not suitable for CI VM

echo starting with param "%1"
set p=%1
if "%p%"=="" set p=all
if "%p%"=="regression" call scripts\call_regression_tests.cmd && powershell write-Host "SUCCESS!" -Foreground Green &&  exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 19 
if "%p%"=="mid" call call_unit_tests.cmd *Integration && powershell write-Host "SUCCESS!" -Foreground Green && exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 20 
if "%p%"=="mid_ext" call call_unit_tests.cmd *Integration:*IntegrationExt && powershell write-Host "SUCCESS!" -Foreground Green && exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 20 
if "%p%"=="mid_ext_long" call call_unit_tests.cmd *Integration:*IntegrationExt:*_Long && powershell write-Host "SUCCESS!" -Foreground Green && exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 20 
if "%p%"=="integration" call scripts\call_integration_tests.cmd && powershell write-Host "SUCCESS!" -Foreground Green && exit /b 0 ||  powershell write-Host "FAIL!" -Foreground Red && exit /b 20 
if not "%p%"=="all" powershell write-Host "Bad parameter %p%" -Foreground Red && exit /b 1
call call_unit_tests.cmd *Integration && powershell write-Host "Success 1" -Foreground Green  ||  powershell write-Host "FAIL 1" -Foreground Red  && exit /b 77
call scripts\call_regression_tests.cmd && powershell write-Host "Success 2" -Foreground Green  ||  powershell write-Host "FAIL 2" -Foreground Red && exit /b 17
call scripts\call_integration_tests.cmd && powershell write-Host "Success 3" -Foreground Green && exit /b 0  ||  powershell write-Host "FAIL 3" -Foreground Red  && exit /b 18
