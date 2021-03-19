@echo off
set shared_fldr=c:\dev\shared_public

powershell Write-Host "%0 is running..."  -Foreground Green
set prdata=ProgramData
if "%1" == "" set root=%cd%\..\..\artefacts&& goto exec_me
set root=%1
powershell Write-Host Setting root to %root% -Foreground Green
:exec_me
set user_dir=%root%\%prdata%\checkmk\agent
if not exist "%root%" powershell Write-Host Making folder %root% -Foreground Yellow && mkdir %root% 2> nul
mkdir %root%\plugins 2> nul
if not exist "%user_dir%" powershell Write-Host Making folder %user_dir% -Foreground Yellow && mkdir %user_dir% 2> nul
mkdir %root%\bin 2> nul
mkdir %root%\utils 2> nul
mkdir %root%\providers 2> nul
mkdir %root%\exe 2> nul
mkdir %root%\pdb 2> nul
mkdir %user_dir%\bin 2> nul

if not exist "..\windows\plugins" powershell Write-Host "Folder agents\windows\plugins doesnt exist. Check prep\checkout routine" -Foreground Red &&  exit /b 33

powershell Write-Host "Installation simulation Root Folder: plugins, ohm, yml"  -Foreground Green
copy ..\windows\plugins\*.*         	%root%\plugins\ > nul || powershell Write-Host "Failed plugins copy" -Foreground Red	&&  exit /b 3
copy .\test_files\ohm\cli\*.*       	%user_dir%\bin\ > nul || powershell Write-Host "Failed ohm copy. Try to kill Open Hardware Monitor: taskkill /F /IM OpenhardwareMonitorCLI.exe" -Foreground Yellow
copy .\install\resources\check_mk.yml  	%root%\ > nul         || powershell Write-Host "Failed check_mk.yml copy" -Foreground Red	&&  exit /b 5

powershell Write-Host "1. Test machine preparation: Shared Folder"  -Foreground Green
if not exist "%shared_fldr%" powershell Write-Host Making folder %shared_fldr% -Foreground Yellow && mkdir %shared_fldr%
copy .\test_files\shared_public     	%shared_fldr% > nul   || powershell Write-Host "Failed shared_public copy" -Foreground Red &&  exit /b 6
powershell Write-Host "You must have in  Shared Folder at least one file with UNICODE name. This file must be created Manually."  -Foreground Cyan
if not exist "%LOGONSERVER%\shared_public" powershell Write-Host Sharing %shared_fldr% -Foreground Yellow && net share shared_public=%shared_fldr% /grant:everyone,FULL 1> nul && Icacls %shared_fldr% /grant Everyone:F /inheritance:e /T 1> nul

powershell Write-Host "2. Test machine preparation: Root Folder"  -Foreground Green
copy .\test_files\config\*.yml 		    %root%\ > nul         || powershell Write-Host "Failed test ymls copy" -Foreground Red	&&  exit /b 7

powershell Write-Host "3. Test machine preparation: User Folder"  -Foreground Green
copy .\test_files\config\*.cfg      	%user_dir% > nul      || powershell Write-Host "Failed test cfgs copy" -Foreground Red	&&  exit /b 8 
copy .\test_files\config\*.test.ini 	%user_dir% > nul	  || powershell Write-Host "Failed test inis copy" -Foreground Red	&&  exit /b 9
copy .\test_files\config\*.test.out 	%user_dir% > nul	  || powershell Write-Host "Failed test outs copy" -Foreground Red	&&  exit /b 10
copy .\test_files\cap\*.test.cap 	    %user_dir% > nul      || powershell Write-Host "Failed test caps copy" -Foreground Red	&&  exit /b 11
copy .\test_files\unit_test\*.ini 	    %user_dir% > nul      || powershell Write-Host "Failed test ini copy" -Foreground Red	&&  exit /b 12
copy .\test_files\unit_test\*.dat 	    %user_dir% > nul      || powershell Write-Host "Failed test dat copy" -Foreground Red	&&  exit /b 13
copy .\test_files\unit_test\*.state 	    %user_dir% > nul      || powershell Write-Host "Failed test state copy" -Foreground Red	&&  exit /b 14
copy .\test_files\config\*.yml 	%user_dir% > nul	  || powershell Write-Host "Failed test ymls copy" -Foreground Red	&&  exit /b 15

