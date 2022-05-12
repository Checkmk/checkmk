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


set shared_fldr=c:\dev\shared_public

%Print%{128;255;0}1. Test machine preparation: Shared Folder\n
if not exist "%shared_fldr%" powershell Write-Host Making folder %shared_fldr% -Foreground Yellow && mkdir %shared_fldr%
xcopy .\test_files\shared_public     	%shared_fldr% /D /Y > nul   || powershell Write-Host "Failed shared_public copy" -Foreground Red &&  exit /b 6
echo You must have in  Shared Folder at least one file with UNICODE name. This file must be created Manually.
if not exist "%LOGONSERVER%\shared_public" powershell Write-Host Sharing %shared_fldr% -Foreground Yellow && net share shared_public=%shared_fldr% /grant:everyone,FULL 1> nul && Icacls %shared_fldr% /grant Everyone:F /inheritance:e /T 1> nul
