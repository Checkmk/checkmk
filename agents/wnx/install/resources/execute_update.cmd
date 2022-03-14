@rem 
@rem ---  Installation script ---
@rem 
@rem Runs few times msi_exec till the installation is successful.
@rem BACKGROUND: If the target folder is locked, than installtion is not possible.
@rem n windows you can lock folder using different methods, reliable one is Far Manager
@rem cd $programfiles(x86)%\checkmk\service and Ctrl-O. Since this moment installation to the folder
@rem will be impossible, because deleted(!) during uninstall(!) folder will be not deleted but locked.

@echo off
rem mandatory to have errorlevel reliable
SETLOCAL EnableDelayedExpansion

if "%5" == "" echo "Usage: execute_update msi_exec command_line own_log_file tgt_msi rev_msi" && exit /b 1
rem Prepare variable
set tgt_file=%4
set rev_file=%5
set log_file=%3
set msi_exec=%1
rem we have to remove double quotes
set cmd_line=%2
set cmd_line=%cmd_line:"=%
set tgt_file=%tgt_file:"=%
set rev_file=%rev_file:"=%


rem Indicate start in log file
echo "Run msi started at %time% with params tgt_file=%tgt_file% rev_file=%rev_file% log_file=%log_file%" >> %log_file%

rem check the msi_exec exists
if not exist %msi_exec% echo "File %msi_exec% doesnt exists" >> %log_file% && exit /b 2
if not exist %tgt_file% echo "File %tgt_file% doesnt exists" >> %log_file% && exit /b 3
if not exist %rev_file% echo "File %rev_file% doesnt exists" >> %log_file%

rem --- PREPARATION: wait 5 seconds and stop service ---
powershell Start-Sleep 5

for /l %%x in (1, 1, 5 ) do (
  rem --- 1st run ---
  echo %%x. [%time%] starting "%msi_exec% /i %tgt_file% %cmd_line%" >> %log_file%
  %msi_exec% /i "%tgt_file%"  %cmd_line% >> %log_file%
  echo finished >> %log_file%

  rem validate result
  sc query | find /i "checkmkservice" >> %log_file%

  rem exclamation marks - fresh idea from Microsoft to calc value dynamically
  if "!errorlevel!" == "0" echo "[+] Installed successfully" >> %log_file% && goto start_service_and_exit
  rem failure!
  echo "[-] Installation failed. Pause & Retry..." >> %log_file%
  powershell Start-Sleep 10
)

echo "[-] Service is not installed, try to install revert msi" >> %log_file% 
move /Y %tgt_file% %tgt_file%.failed >> %log_file%
if not exist "%rev_file%" echo "[-] No rev file %rev_file%" >> %log_file%  && goto start_service_and_exit
move /Y %rev_file% %tgt_file% >> %log_file%

for /l %%x in (1, 1, 5 ) do (
  rem --- 1st run ---
  echo %%x. [%time%] starting "%msi_exec% /i %tgt_file% %cmd_line%" >> %log_file%
  %msi_exec% /i "%tgt_file%" %cmd_line% >> %log_file%
  echo finished >> %log_file%

  rem validate result
  sc query | find /i "checkmkservice" >> %log_file%

  rem exclamation marks - fresh idea from Microsoft to calc value dynamically
  if "!errorlevel!" == "0" echo "[+] Installed from backup successfully" >> %log_file% && goto start_service_and_exit
  rem failure!
  echo "[-] Installation failed. Pause & Retry..." >> %log_file%
  powershell Start-Sleep 10
)

echo "[-] Service is not installed" >> %log_file% 


:start_service_and_exit
echo "starting service for safety" >> %log_file%
net start checkmkservice >> %log_file%
exit /b 0

