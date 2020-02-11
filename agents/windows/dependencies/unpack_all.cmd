@echo off
if "%1%" == "" powershell Write-Host "Invalid 1-st param, smth like to \omd\packages" -ForegroundColor Red && goto usage
if "%2%" == "" powershell Write-Host "Invalid 2-nd param, smth like to agent\windows\dependencies" -ForegroundColor Red && goto usage
if "%3%" == "" powershell Write-Host "Invalid 3-rd param, must be path to output" -ForegroundColor Red && goto usage

set omd_path=%1%
set agent_path=%2%
if not exist "%agent_path%" powershell Write-Host "%agent_path% not found, using %omd_path%" -ForegroundColor red  && goto end
set unpacker_exe=%agent_path%\7-zip\7z.exe
set unpacker=%unpacker_exe% x -y
if not exist "%unpacker_exe%" powershell Write-Host "%unpacker_exe% not found" -ForegroundColor red  && goto end
set out_root=%3%
set unpack_cmd=%agent_path%\unpack_package.cmd
if not exist "%unpack_cmd%" powershell Write-Host "%unpack_cmd% not found" -ForegroundColor red  && goto end

rem with internal folder in the tar.gz
set nm=googletest
set vv=-release-1.10.0
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% *

rem with internal folder in the tar.gz
set nm=catch2
set vv=-master-2.4.2
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% *

rem with internal folder in the tar.gz
set nm=asio
set vv=-asio-1-14-0
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% *
rem specific asio, renaming asio/asio to asio
set top_folder=%out_root%\%out_dir_name%
rename %top_folder% tmp
move %out_root%\tmp\asio %top_folder%
rmdir /q/s %out_root%\tmp

rem with internal folder in the tar.gz
set nm=fmt
set vv=-master-6.1.0
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% *

rem with internal folder in the tar.gz
set nm=yaml-cpp
set vv=-master
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% *

rem with internal folder in the tar.gz
set nm=json
set vv=-master-3.4.0
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% *


rem without internal folder in the tar.gz
set nm=simpleini
set vv=-2af65fc
set src_dir_name=%omd_path%\%nm%
if not exist %src_dir_name% set src_dir_name=%agent_path%\%nm%
set src_file_name=%nm%%vv%
set out_dir_name=%nm%
powershell Write-Host "%out_dir_name%:" -ForegroundColor blue
call %unpack_cmd% %unpacker_exe% %src_dir_name% %src_file_name% %out_root% %out_dir_name% %out_dir_name%

goto end
:usage
powershell Write-Host "Usage example:" -ForegroundColor Red
powershell Write-Host "%0% ..\..\..\omd\packages . ..\mypacks" -ForegroundColor DarkGreen
:end
