@echo off
rem Guest-side, for watest-qemu (watest_qemu.py): creates the shared_public
rem share (watest-qemu-share.ps1), then runs watest.exe with the gtest
rem filter in %1, with the staged tree as its WNX_TEST_ROOT.
set WNX_TEST_ROOT=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0watest-qemu-share.ps1" || (echo error: creating the shared_public share failed& exit /b 1)
"%~dp0watest.exe" %1
