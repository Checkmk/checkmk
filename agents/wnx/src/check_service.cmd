@echo off
if not exist %REMOTE_MACHINE% echo "error..................." goto end
if exist %REMOTE_MACHINE% copy ..\test_files\config\*.yml %REMOTE_MACHINE% > nul
:end
