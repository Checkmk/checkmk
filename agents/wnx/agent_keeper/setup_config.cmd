@echo off
:: Script to define mandatory variables individual for the project

:: for the run.cmd
set worker_name=agent_keeper
:: artefacts
set worker_exe_name=agent_keeper.exe
:: relative location 
set worker_root_dir=%cd%\..\..\..
:: Rust
set worker_target=i686-pc-windows-msvc
:: Elevation
set worker_need_elevation=1

exit /b 0