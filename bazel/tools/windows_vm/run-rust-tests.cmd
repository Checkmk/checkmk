@echo off
rem Guest-side, for the Rust packages' *-tests-qemu runners: runs every
rem test binary (*.exe) next to this script with the arguments in %*, each
rem also after one failed, from the stage's root, where the tests find what
rem they test. The exit code is 1 if any failed: neq 0, not errorlevel 1, as
rem a crash exits with a negative NTSTATUS. It is also 1 when the session
rem is not elevated, as tests that need elevation would skip themselves and
rem pass, and when the stage has no test binary at all.
net session >nul 2>&1 || (echo error: the session is not elevated& exit /b 1)
set rc=0
set n=0
for %%t in ("%~dp0*.exe") do (set /a n+=1 & call :run "%%~t" %*)
if %n%==0 (echo error: no test binaries next to %~nx0& exit /b 1)
exit /b %rc%

:run
echo === %~nx1
%*
if %ERRORLEVEL% neq 0 set rc=1
exit /b 0
