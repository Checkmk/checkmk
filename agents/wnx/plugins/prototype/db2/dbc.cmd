rem ORIGINAL CODE FROM IBM how to run command(set variables and bla-bla-bla)

set PATH=%~d0%~p0..\db2tss\bin;%PATH%
for /f "delims=?" %%n in ('%~d0"%~p0"db2clpsetcp') do %%n
if /i "%COMSPEC%" == "%WINDIR%\system32\cmd.exe" goto WINNT

:WIN95
@%1 %2 %3 %4 %5 %6 %7 %8 %9
@goto END

:WINNT
@%*

pause
:END
