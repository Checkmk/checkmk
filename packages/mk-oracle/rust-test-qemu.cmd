@echo off
rem Guest-side, for mk-oracle-tests-qemu (rust_test_qemu.py): points
rem MK_CONFDIR and MK_LIBDIR into the stage, where the runtime-detection
rem tests find the OCI client, then runs the test binaries with the
rem arguments in %* (run-rust-tests.cmd).
set "MK_CONFDIR=%~dp0packages\mk-oracle"
set "MK_LIBDIR=%~dp0packages\mk-oracle\runtimes"
call "%~dp0run-rust-tests.cmd" %*
