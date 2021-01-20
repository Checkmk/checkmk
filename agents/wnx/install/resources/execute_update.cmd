@echo off
if "%3" == "" echo "Usage: execute_update msi_exec "command line" own_log_file" && exit /b 1
rem Prepare variable
set log_file=%3
set msi_exec=%1
rem we have to remove double quotes
set cmd_line=%2
set cmd_line=%cmd_line:"=%


rem Indicate start in log file
echo "Run msi started at %time%" >> %log_file%

rem check the msi_exec exists
if not exist %msi_exec% echo "File %msi_exec% doesnt exists" >> %log_file% && exit /b 2

rem --- 1st run ---
echo 1. [%time%] starting "%msi_exec% %cmd_line%" >> %log_file%
%msi_exec% %cmd_line% >> %log_file%
echo finished >> %log_file%

rem validate result
sc query | find /i "checkmkservice" >> %log_file%
if "%errorlevel%" == "0" echo "[+] Installed successfully" >> %log_file% && exit /b 0
rem failure!
echo "[-] Installation failed. Pause & Retry..." >> %log_file%
powershell Start-Sleep 5

rem --- 2nd run ---
echo 2. [%time%] starting "%msi_exec% %cmd_line%" >> %log_file%
%msi_exec% %cmd_line% >> %log_file%
echo finished >> %log_file%

rem validate result
sc query | find /i "checkmkservice" >> %log_file%
if "%errorlevel%" == "0" echo "[+] Installed successfully" >> %log_file% && exit /b 0
rem failure!
echo "[-] Installation failed. Pause & Retry..." >> %log_file%
powershell Start-Sleep 5

rem --- 3rd run ---
echo 3. [%time%] starting "%msi_exec% %cmd_line%" >> %log_file%
%msi_exec% %cmd_line% >> %log_file%
echo finished >> %log_file%

rem validate result
sc query | find /i "checkmkservice" >> %log_file%
if "%errorlevel%" == "0" echo "[+] Service is presented" >> %log_file% && exit /b 0
echo "[-] Service is not installed" >> %log_file% && exit /b 3

