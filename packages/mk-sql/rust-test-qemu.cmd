@echo off
rem Guest-side, for mk-sql-tests-qemu (rust_test_qemu.py): checks that the
rem image has the SQL Server instances the tests expect, loads the registry
rem test sets as the legacy nodes do (manage-test-registry-set.ps1), then
rem runs the test binaries with the arguments in %* (run-rust-tests.cmd).
rem The remote tests use the guest's own SQL Server over TCP, as sa (see
rem install-mssql.ps1).
for %%i in (MSSQLSERVER SQLEXPRESS_NAME SQLEXPRESS_WOW) do (
  reg query "HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL" /v %%i >nul 2>&1 || (echo error: SQL Server instance %%i is missing in this image& exit /b 1)
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tests\files\ci-scripts\manage-test-registry-set.ps1" --reinstall 2.5.0 || (echo error: loading the test registry failed& exit /b 1)
set "CI_TEST_SQL_DB_ENDPOINT=localhost:sa:%QEMU_VM_PASSWORD%"
call "%~dp0run-rust-tests.cmd" %*
