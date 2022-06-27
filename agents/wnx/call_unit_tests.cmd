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



set arte=%cd%\..\..\artefacts
set results=unit_tests_results.zip

if "%1" == "SIMULATE_OK" powershell Write-Host "Unit test SUCCESS" -Foreground Green  && exit /b 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Unit test FAIL" -Foreground Red && del %arte%\check_mk_service.msi && exit /b 100
if NOT "%1" == "" set param=--gtest_filter=%1
set sec_param=%2
if "%param%" == "" powershell Write-Host "Full and Looooooong test was requested." -Foreground Cyan && set sec_param=both
if "%param%" == "*Integration" powershell Write-Host "Mid tests" -Foreground Cyan && set results=mid_tests_results.zip

%Print%{255;255;255}32-bit test\n
::call build_watest.cmd %sec_param%
::if not %errorlevel% == 0 echo "build failed" goto error

set WNX_TEST_ROOT=%temp%\test_%random%
mkdir %WNX_TEST_ROOT%
call prepare_to_tests.cmd %WNX_TEST_ROOT%\test
mklink %WNX_TEST_ROOT%\watest32.exe %arte%\watest32.exe 
net stop WinRing0_1_2_0
%WNX_TEST_ROOT%\watest32.exe %param%
if not %errorlevel% == 0 powershell Write-Host "This is ERROR %errorlevel% in testing 32" -Foreground Red && goto error
if NOT "%sec_param%" == "both" powershell Write-Host "This is end of testing. QUICK test was requested." -Foreground Cyan && goto success

@rem 64-bit is tested quickly
powershell Write-Host "64-bit test" -Foreground Cyan
if "%1" == "" set param=--gtest_filter=-PluginTest.Sync*:PluginTest.Async*
mklink %WNX_TEST_ROOT%\watest32.exe %arte%\watest32.exe 
WNX_TEST_ROOT%\watest64.exe %param%
if not %errorlevel% == 0 powershell Write-Host "This is ERROR %errorlevel% in testing 64" -Foreground Red && goto error
%Print%{0;255;255}This is end of testing. FULL test was requested.\n
:success
%Print%{0;255;0}Unit test "%param%": SUCCESS\n
call :zip_results
exit /b 0
:error
%Print%{255;0;0} Unit test "%param%": failed with error level "%errorlevel%" \n
call :zip_results
exit /b 78

:zip_results
ren %arte%\%results% %arte%\%results%.bak 2> nul
pushd %WNX_TEST_ROOT% && ( call :zip_and_remove & popd )
exit /b

:zip_and_remove
echo zipping results with remove
7z a -r -y -tzip %arte%\%results% >nul 
rmdir /s/q "%WNX_TEST_ROOT%" 2>nul
exit /b
