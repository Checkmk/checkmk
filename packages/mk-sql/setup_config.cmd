@echo off
:: Script to define mandatory variables individual for the project

if "%CI_TEST_SQL_DB_ENDPOINT%" == "" echo "CI_TEST_SQL_DB_ENDPOINT is not defined, full testing is impossible"

:: for the run.cmd
set worker_name=mk-sql
:: artefacts
set worker_exe_name=mk-sql.exe
:: relative location
set worker_root_dir=%cd%\..\..
:: Rust
set worker_target=i686-pc-windows-msvc
set worker_toolchain=1.87

exit /b 0
