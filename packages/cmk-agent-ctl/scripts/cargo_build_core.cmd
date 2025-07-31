@echo off
:: Script to Build Rust executable and sign it
::
:: Sign mode:
:: cargo_build_core file password
:: file is located in c:\common\store and must be well protected from access
:: The password is delivered by jenkins(in a turn from our password store)
:: In future we could download file too(from the password store), but this will
:: not change the requirement to protect the file from free access.
::
:: Standard Mode:
:: cargo_build_core
::

SETLOCAL EnableDelayedExpansion

set RUST_BACKTRACE=1

if "%worker_arte%" == "" powershell Write-Host "worker_arte is not defined" -Foreground Red && exit /b 79
if "%worker_cur_dir%" == "" powershell Write-Host "worker_cur_dir is not defined" -Foreground Red && exit /b 79
if "%worker_root_dir%" == "" powershell Write-Host "worker_root_dir is not defined" -Foreground Red && exit /b 79
if "%worker_exe_name%" == "" powershell Write-Host "worker_exe_name is not defined" -Foreground Red && exit /b 79
if "%worker_target%" == "" powershell Write-Host "worker_target is not defined" -Foreground Red && exit /b 79
if "%worker_toolchain%" == "" powershell Write-Host "worker_target is not defined" -Foreground Red && exit /b 79


:: Jenkins calls windows scripts in a quite strange manner, better to check is cargo available
where cargo > nul
if not %errorlevel% == 0 powershell Write-Host "Cargo not found, please install it and/or add to PATH" -Foreground Red && exit /b 7
rustup update
echo rustup target add %worker_target% --toolchain %worker_toolchain%
rustup target add %worker_target% --toolchain %worker_toolchain%

:: 64-bit
::set target=x86_64-pc-windows-mscvc
:: 32-bit
set exe=target\%worker_target%\release\%worker_exe_name%
@echo RUST versions:
cargo -V
rustc -V
echo Settings:
echo worker_arg_build=%worker_arg_build%
echo worker_arg_clippy=%worker_arg_clippy%
echo worker_arg_test=%worker_arg_test%
echo worker_target=%worker_target%
echo worker_toolchain=%worker_toolchain%

:: Disable assert()s in C/C++ parts (e.g. wepoll-ffi), they map to _assert()/_wassert(),
:: which is not provided by libucrt. The latter is needed for static linking.
:: https://github.com/rust-lang/cc-rs#external-configuration-via-environment-variables
set CFLAGS=-DNDEBUG

:: Clean
if "%worker_arg_clean%" == "1" (
    powershell Write-Host "Run Rust clean" -Foreground White
    cargo clean
)

:: Check Format
if "%worker_arg_check_format%" == "1" (
    powershell Write-Host "Run Rust check format" -Foreground White
    cargo fmt -- --check
)

:: Format
if "%worker_arg_format%" == "1" (
    powershell Write-Host "Run Rust format" -Foreground White
    cargo fmt
)

:: Clippy
if "%worker_arg_clippy%" == "1" (
    powershell Write-Host "Run Rust clippy" -Foreground White
    cargo clippy --release --target %worker_target% --tests -- --deny warnings
    if ERRORLEVEL 1 (
        powershell Write-Host "Failed cargo clippy" -Foreground Red
        exit /b 17
    ) else (
        powershell Write-Host "Checking Rust SUCCESS" -Foreground Green
    )
) else (
    powershell Write-Host "Skip Rust clippy" -Foreground Yellow
)

:: Build
if "%worker_arg_build%" == "1" (
    rem On windows we want to kill exe before starting rebuild.
    rem Use case CI starts testing, for some reasoms process hangs up longer as expected thus
    rem rebuild/retest will be not possible: we get strange/inconsistent results.
    call %worker_root_dir%\scripts\windows\kill_processes_in_targets.cmd %worker_target%\release || echo: ok...
    del /Q %worker_arte%\%worker_exe_name% 2> nul

    powershell Write-Host "Building Rust executables" -Foreground White
    cargo build --release --target %worker_target% 2>&1
    if ERRORLEVEL 1 (
        powershell Write-Host "Failed cargo build" -Foreground Red
        exit /b 18
    ) else (
        powershell Write-Host "Building Rust SUCCESS" -Foreground Green
    )
) else (
    powershell Write-Host "Skip Rust build" -Foreground Yellow
)

:: Test
if "%worker_arg_test%" == "1" (
rem Validate elevation, because full testing is possible only in elevated mode!
  
    if "%worker_need_elevation%" == "1" (
        net session > nul 2>&1
        IF ERRORLEVEL 1 (
            echo You must be elevated. Exiting...
            exit /B 21
        )
    )
    powershell Write-Host "Testing Rust executables" -Foreground White
    cargo test --release --target %worker_target% -- --test-threads=4 2>&1
    if ERRORLEVEL 1  (
        powershell Write-Host "Failed cargo test" -Foreground Red
        exit /b 19
    ) else (
        powershell Write-Host "Testing Rust SUCCESS" -Foreground Green
    )
) else (
    powershell Write-Host "Skip Rust test" -Foreground Yellow
)

:: [optional] Signing
if "%worker_arg_sign%" == "1" (
    powershell Write-Host "Signing Rust executables" -Foreground White
    @call %worker_root_dir%\agents\wnx\sign_windows_exe c:\common\store\%worker_arg_sign_file% %worker_arg_sign_secret% %exe%
    if ERRORLEVEL 1 (
        powershell Write-Host "Failed signing %exe%" -Foreground Red
        exit /b 20
    )
) else (
    powershell Write-Host "Skip Rust sign" -Foreground Yellow
)

:: 5. Storing artifacts
if "%worker_arg_build%" == "1" (
    powershell Write-Host "Uploading artifacts: [ %exe% ] ..." -Foreground White
    copy %exe% %worker_arte%\%worker_exe_name%
    if ERRORLEVEL 1 (
        powershell Write-Host "Failed to copy %exe%" -Foreground Red
        exit /b 22
    ) else (
        powershell Write-Host "Done." -Foreground Green
    )
) else (
    powershell Write-Host "Skip Rust upload" -Foreground Yellow
)

:: Documentation
if "%worker_arg_doc%" == "1" (
    powershell Write-Host "Creating documentation" -Foreground White
    cargo doc
) else (
    powershell Write-Host "Skip creating documentation" -Foreground Yellow
)


