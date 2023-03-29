@echo off
if "%1%" == "" powershell Write-Host "Invalid unpacker" -ForegroundColor Red && goto usage
if "%2%" == "" powershell Write-Host "Invalid src dir name" -ForegroundColor Red && goto usage
if "%3%" == "" powershell Write-Host "Invalid src file name" -ForegroundColor Red && goto usage
if "%4%" == "" powershell Write-Host "Invalid out dir root" -ForegroundColor Red && goto usage
if "%5%" == "" powershell Write-Host "Invalid out dir name" -ForegroundColor Red && goto usage
if "%6%" == "" powershell Write-Host "Folder Correction not set" -ForegroundColor Red && goto usage

set unpacker_exe=%1
set unpacker=%unpacker_exe% x -y

set src_dir_name=%2
set src_file_name=%3
set src_full_file_name=%src_dir_name%\%src_file_name%
set tgz=%src_full_file_name%.tar.gz

if not exist "%tgz%" powershell Write-Host "%tgz% not found" -ForegroundColor Red && goto exit
powershell Write-Host "%src_full_file_name% to be used as src" -ForegroundColor green

set out_root_dir=%4%
mkdir %4% > nul
powershell Write-Host "Output root folder %out_root_dir% made/exist" -ForegroundColor green

set out_dir_name=%5%
set out_full_dir=%out_root_dir%\%out_dir_name%
powershell Write-Host "%out_full_dir% set to" -ForegroundColor green

if "%6%" == "*"  ( 
rem we will rename output file name into something more readable
set out_folder=
) else (
rem we will unpack to folder without changes
set out_folder=/%6%
)

set tar=%out_root_dir%\%src_file_name%.tar
rem if not exist "%x_folder%" powershell Write-Host "Folder %x_folder% not found" -ForegroundColor Red && goto exit
if not exist "%tgz%" powershell Write-Host "File %tgz% not found" -ForegroundColor Red && goto exit

rem if exist "%root_folder%\%dir_name%" powershell Write-Host "%dir_name% already installed" -ForegroundColor Green && goto exit:
powershell Write-Host "Installing '%tgz%' to '%out_full_dir%'" -ForegroundColor DarkGreen
if exist "%out_full_dir%" powershell Write-Host "'%out_full_dir%' exists" -ForegroundColor Cyan && goto exit:
powershell Write-Host "Unpacking '%tgz%' to %out_root_dir%" -ForegroundColor DarkGreen
%unpacker% "%tgz%" -aos -o"%out_root_dir%" > nul
if not exist "%tar%" powershell Write-Host "'%tar%' not found, decompression failed" -ForegroundColor Red && goto exit:
powershell Write-Host "Unpacking '%tar%' to %out_root_dir%%out_folder%" -ForegroundColor DarkGreen
%unpacker% "%tar%" -aos -o"%out_root_dir%%out_folder%" > nul
del %tar%
if "%out_folder%" == "" (
powershell Write-Host "Renaming %src_file_name%" "%out_dir_name%" -ForegroundColor DarkGreen
rename "%out_root_dir%\%src_file_name%" "%out_dir_name%"
)

rem CAREFUL WITH LINE BELOW!
if not "%out_root_dir%" == "" del /Q "%out_root_dir%\*.*" && powershell Write-Host "cleaned '%out_root_dir%'" -ForegroundColor Green
if exist "%root_folder%\%dir_name%" (
powershell Write-Host "'%out_dir_name%' installed successfully " -ForegroundColor Green
) else (
powershell Write-Host "'%out_dir_name%' install failed" -ForegroundColor Red
)
goto exit
:usage
powershell Write-Host "Usage:" -ForegroundColor DarkGreen
powershell Write-Host "unpack_package.cmd file_name target_dir_name sourcedir_name" -ForegroundColor DarkGreen
powershell Write-Host "sourcedir_name is subdirectory in ..\omd\packages" -ForegroundColor DarkGreen
powershell Write-Host "Example with folder in tarball:" -ForegroundColor DarkGreen
powershell Write-Host "       unpack_package.cmd 7z ..\..\..\third_party\googletest googletest-71140c3ca7-patched.tar.gz ..\packages2 googletest *" -ForegroundColor DarkGreen
powershell Write-Host "Example without folder in tarball: unpack_package.cmd simpleini-2af65fc simpleini simpleini 7-zip\7z.exe ..\packagesx simpleini" -ForegroundColor DarkGreen
:exit
