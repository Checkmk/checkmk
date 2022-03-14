:: Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
:: This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
:: conditions defined in the file COPYING, which is part of this source code package.

:: Script to sign arbitrary windows exe with provided pfx file and password
:: Usage: sign_windows_exe.cmd pfx_file password exe_file
:: 
:: pfx file must be obtained with the help of the Certificate provider(for example Comodo)
::
:: To obtain certificate:
:: 1. Buy certificate
:: 2. Identify company and self. This is long and complicated process.
:: 3. Request Certificate: Supply CSR - use Internet Explorer to generate it
:: 4. After successful verification you will get a mail with a link.
:: 5. Use Internet Explorer to get install certificate using link from p.4.
:: 6. Export obtained certificate with private key.
:: 7. Deliver exported certificate(pfx file) and password to the CI team.
:: 8. Use this script to sign exe.
:: *) Read documentation carefully and do not hesitate to ping tech support.
::

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

if "%3" == "" (
%Print%{255;0;0}Invalid parameters\n
%Print%{0;255;0}Usage: 
%Print%{255;255;255}sign_windows_exe.cmd pfx_file password exe_file\n
exit /b 1
)

%Print%{255;255;255}Signing %3 using key %1\n
@"C:\Program Files (x86)\Microsoft SDKs\ClickOnce\SignTool\signtool.exe" sign /tr http://timestamp.digicert.com /fd sha256 /td sha256 /f %1 /p %2 %3
exit /b 0