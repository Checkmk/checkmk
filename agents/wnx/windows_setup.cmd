@echo off
net file 1>nul 2>nul & if errorlevel 1 (echo Admin rights are required to run this script. Exiting... & echo. &  exit /D)
:: ... proceed here with admin rights ..

cd scripts\os_setup
call setup_choco.cmd
call wc1.cmd
call wc2.cmd
call wc3.cmd
cd ..\..