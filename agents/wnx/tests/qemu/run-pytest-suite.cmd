@echo off
rem Guest-side, for the *-qemu runners of the pytest suites
rem (wnx_pytest_suite.py): runs agents\wnx\tests\%1 on the test Python,
rem unpacked from python-test.cab, from repo\agents\wnx, with the suite's
rem WNX_*_BASE_DIR that wnx_pytest_suite.run() sets.
rem
rem No firewall rules: the suites only connect over loopback, which Windows
rem Firewall does not filter. The logs and configs the agent left in base\
rem end up in logs.tgz, for triage. The exit code is pytest's.
mkdir %QEMU_GDIR%\python
expand -F:* %QEMU_GDIR%\python-test.cab %QEMU_GDIR%\python >nul || exit /b 1
cd /d %QEMU_GDIR%\repo\agents\wnx
set repo_root=%QEMU_GDIR%\repo
%QEMU_GDIR%\python\python.exe -m pytest tests\%1
set rc=%ERRORLEVEL%
robocopy %QEMU_GDIR%\base %QEMU_GDIR%\logs *.log *.yml /s >nul
tar -czf %QEMU_GDIR%\logs.tgz -C %QEMU_GDIR%\logs . >nul 2>&1
exit /b %rc%
