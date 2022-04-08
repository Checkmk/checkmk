@Echo Off & Setlocal DisableDelayedExpansion
::: do not need this
::: mode 170,40 

::: { Creates variable /AE = Ascii-27 escape code.
::: - %/AE% can be used  with and without DelayedExpansion.
    For /F %%a in ('echo prompt $E ^| cmd')do set "/AE=%%a"
::: }

(Set \n=^^^
%=Newline DNR=%
)
::: / Color Print Macro -
::: Usage: %Print%{RRR;GGG;BBB}text to output
::: \n at the end of the string echo's a new line
::: valid range for RGB values: 0 - 255
  Set Print=For %%n in (1 2)Do If %%n==2 (%\n%
    For /F "Delims=" %%G in ("!Args!")Do (%\n%
      For /F "Tokens=1 Delims={}" %%i in ("%%G")Do Set "Output=%/AE%[0m%/AE%[38;2;%%im!Args:{%%~i}=!"%\n%
      ^< Nul set /P "=!Output:\n=!%/AE%[0m"%\n%
      If "!Output:~-2!"=="\n" (Echo/^&Endlocal)Else (Endlocal)%\n%
    )%\n%
  )Else Setlocal EnableDelayedExpansion ^& Set Args=
::: / Erase Macro -
::: Usage: %Erase%{string of the length to be erased}
  Set Erase=For %%n in (1 2)Do If %%n==2 (%\n%
    For /F "Tokens=1 Delims={}" %%G in ("!Args!")Do (%\n%
      Set "Nul=!Args:{%%G}=%%G!"%\n%
      For /L %%# in (0 1 100) Do (If Not "!Nul:~%%#,1!"=="" ^< Nul set /P "=%/AE%[D%/AE%[K")%\n%
    )%\n%
    Endlocal%\n%
  )Else Setlocal EnableDelayedExpansion ^& Set Args=


if "%1" == "" (
  %Print%{255;0;0}Dir is absent \n 
  exit /b 33
)
%Print%{0;255;0}%0 is running... \n
set root=%1\root
set data=%1\data
set user_dir=%data%
if not exist "%root%" (
  %Print%{0;255;255}Making folder %root% ... \n
  mkdir %root% 2> nul
)
mkdir %root%\plugins 2> nul

if not exist "%user_dir%" (
  %Print%{0;255;255}Making folder %user_dir% \n
  mkdir %user_dir% 2> nul
)
mkdir %user_dir%\bin 2> nul

if not exist "..\windows\plugins" powershell Write-Host "Folder agents\windows\plugins doesnt exist. Check prep\checkout routine" -Foreground Red &&  exit /b 33

%Print%{128;255;0}Installation simulation Root Folder: plugins, ohm, yml\n
xcopy ..\windows\plugins\*.*         	%root%\plugins /D /Y > nul || powershell Write-Host "Failed plugins copy" -Foreground Red	&&  exit /b 3
xcopy .\test_files\ohm\cli\*.*       	%user_dir%\bin /D /Y > nul || powershell Write-Host "Failed ohm copy. Try to kill Open Hardware Monitor: taskkill /F /IM OpenhardwareMonitorCLI.exe" -Foreground Yellow
xcopy .\install\resources\check_mk.yml  	%root% /D /Y> nul         || powershell Write-Host "Failed check_mk.yml copy" -Foreground Red	&&  exit /b 5

%Print%{128;255;0}1. Test machine preparation: Root Folder\n
xcopy .\test_files\config\*.yml 		    %root% /D /Y> nul         || powershell Write-Host "Failed test ymls copy" -Foreground Red	&&  exit /b 7

%Print%{128;255;0}2. Test machine preparation: User Folder\n
xcopy .\test_files\config\*.cfg      	%user_dir% /D /Y> nul      || powershell Write-Host "Failed test cfgs copy" -Foreground Red	&&  exit /b 8 
xcopy .\test_files\config\*.test.ini 	%user_dir% /D /Y> nul	  || powershell Write-Host "Failed test inis copy" -Foreground Red	&&  exit /b 9
xcopy .\test_files\config\*.test.out 	%user_dir% /D /Y> nul	  || powershell Write-Host "Failed test outs copy" -Foreground Red	&&  exit /b 10
xcopy .\test_files\cap\*.test.cap 	    %user_dir% /D /Y> nul      || powershell Write-Host "Failed test caps copy" -Foreground Red	&&  exit /b 11
xcopy .\test_files\unit_test\*.ini 	    %user_dir% /D /Y> nul      || powershell Write-Host "Failed test ini copy" -Foreground Red	&&  exit /b 12
xcopy .\test_files\unit_test\*.dat 	    %user_dir% /D /Y> nul      || powershell Write-Host "Failed test dat copy" -Foreground Red	&&  exit /b 13
xcopy .\test_files\unit_test\*.state 	    %user_dir% /D /Y> nul      || powershell Write-Host "Failed test state copy" -Foreground Red	&&  exit /b 14
xcopy .\test_files\config\*.yml 	%user_dir% /D /Y > nul	  || powershell Write-Host "Failed test ymls copy" -Foreground Red	&&  exit /b 15

