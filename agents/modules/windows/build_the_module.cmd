@rem Main buidling script for Python

@echo off
@if "%1"=="python" goto python_build 
@if "%1"=="success" goto success_build 
@if "%1"=="fail" goto fail_build 
goto usage

:success_build
powershell Write-Host 'Simulating success build...' -foreground Cyan
@powershell Write-Host 'Warning: This is success build to test jenkins pipeline' -foreground Yellow
@powershell Write-Host 'Build Success' -foreground Green
exit /b 0

:fail_build
powershell Write-Host 'Simulating fail build...' -foreground Cyan
@powershell Write-Host 'Warning: This is fail build to test jenkins pipeline' -foreground Yellow
@powershell Write-Host 'Build Fail' -foreground Red
exit /b 11

:python_build
powershell Write-Host 'Building python...' -foreground Cyan
make 
goto exit

:usage:
@rem we are using powershell to call the executable with admin rights and wait
@rem this trick is required to install python in non very interactive environments
@rem like jenkins build
@if "%1"==""  powershell Write-Host "Possible parameters:`n `tpython `t- builds python module`n`tsuccess`t- always return success`n`tfail `t- always returns fail" -foreground Cyan && exit /b 9

:exit