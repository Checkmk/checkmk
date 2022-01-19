@echo off
:: Script to Build Rust executable and sing it
:: 
:: Sign mode:
:: cargo_build file password
:: file is located in c:\common\store and must be well protected from access
:: Password is from jenkins(in a turn from our password store)
:: In future we could download file too(from the password store), but this will 
:: not change the requirement to protect the file from access
::
:: Standard Mode:
:: cargo_build
::

SETLOCAL EnableDelayedExpansion

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
set target=i686-pc-windows-msvc
set exe_name=cmk-agent-ctl.exe
set exe=target\%target%\release\%exe_name%

powershell Write-Host "Building Executables" -Foreground White
cargo build --release --target %target%
if not %errorlevel% == 0 powershell Write-Host "Failed cargo build" -Foreground Red && exit /b 8

if not "%2" == "" (
powershell Write-Host "Signing Executables" -Foreground White
@call ..\wnx\sign_windows_exe c:\common\store\%1 %2 %exe%
if not %errorlevel% == 0 powershell Write-Host "Failed signing %exe%" -Foreground Red && exit /b 9
)

powershell Write-Host "Uploading artifacts: [ %exe% ] ..." -Foreground White
copy %exe% %arte%\%exe_name%
powershell Write-Host "Done." -Foreground Green

