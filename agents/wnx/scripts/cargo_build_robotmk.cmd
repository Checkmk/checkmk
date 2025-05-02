@echo off
:: Script to Build Rust executable and sign it
:: 
:: Sign mode:
:: cargo_build file password
:: file is located in c:\common\store and must be well protected from access
:: The password is delivered by jenkins(in a turn from our password store)
:: In future we could download file too(from the password store), but this will 
:: not change the requirement to protect the file from free access.
::
:: Standard Mode:
:: cargo_build
::

SETLOCAL EnableDelayedExpansion

echo --- info ---
echo PATH=%path%
echo ------------
set RUST_BACKTRACE=1

:: Jenkins calls windows scripts in a quite strange manner, better to check is cargo available
where cargo > nul
if not %errorlevel% == 0 powershell Write-Host "Cargo not found, please install it and/or add to PATH" -Foreground Red && exit /b 7

set cur_dir=%cd%
set output_dir=%cur_dir%\..\..\..\..\artefacts
set target=i686-pc-windows-msvc
set exe_name=robotmk_ext.exe
set exe=target\%target%\release\%exe_name%
rustup toolchain list
rustup default 1.72.0
rustup target add %target%
rustup update 1.72.0

:: Build
powershell Write-Host "Building Rust executables" -Foreground White
cargo build --release --target %target% 2>&1
if ERRORLEVEL 1 (
        powershell Write-Host "Failed cargo build" -Foreground Red 
        exit /b 18
)
powershell Write-Host "Building Rust SUCCESS" -Foreground Green
:: Storing artifacts
powershell Write-Host "Uploading artifacts: [ %exe% ] ..." -Foreground White
copy %exe% %output_dir%\%exe_name%
powershell Write-Host "Done." -Foreground Green
