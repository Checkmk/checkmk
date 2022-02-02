:: Builds Agent controller
:: This is simple wrapper

@echo off
if "%1" == "" powershell Write-Host "param is absent" -foreground red && exit /b 1

powershell Write-Host "executing rust build in %1" -foreground white
pushd %1
call cargo_build.cmd
popd