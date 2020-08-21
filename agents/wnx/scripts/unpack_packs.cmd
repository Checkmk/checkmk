@echo off       
rem check and prepare output folder for smooth deploy and testing
if not "%VS_DEPLOY%" == "YES" goto unpack_all
if not exist %REMOTE_MACHINE% echo Error, REMOTE_MACHINE not defined && goto unpack_all
if not exist %LOCAL_IMAGES_EXE% echo Error, LOCAL_IMAGES_EXE not defined && goto unpack_all
if not exist %LOCAL_IMAGES_PDB% echo Error, LOCAL_IMAGES_PDB not defined && goto unpack_all
if not exist %REMOTE_MACHINE%\bin mkdir %REMOTE_MACHINE%\bin
if not exist %REMOTE_MACHINE%\utils mkdir %REMOTE_MACHINE%\utils
if not exist %REMOTE_MACHINE%\plugins mkdir %REMOTE_MACHINE%\plugins
if not exist %REMOTE_MACHINE%\local mkdir %REMOTE_MACHINE%\local
if not exist %REMOTE_MACHINE%\watest mkdir %REMOTE_MACHINE%\watest
:unpack_all
set out=extlibs
set first=1
:recheck
if not exist %out% echo "no %out%" && goto install
if not exist %out%\googletest echo "no googletest" &&  goto install
if not exist %out%\simpleini echo "no simpleini" && goto install
if not exist %out%\asio echo "no asio" && goto install
if not exist %out%\fmt echo "no fmt" && goto install
if not exist %out%\yaml-cpp echo "no yaml-cpp" && goto install
if not exist %out%\asio\include\asio.hpp "no asio.hpp" && goto install
echo package check success
goto end
:install
@7z -? > nul 2>&1
@if "%errorlevel%" NEQ "0" powershell Write-Host "7zip must be installed: use choco or windows_setup" -Foreground Red && exit /b 1
@powershell Write-Host "[+] 7zip found" -Foreground Green
if "%first%" == "1" (
echo try to unpack
call scripts\unpack_all.cmd ..\..\omd\packages %out%
set first=0
goto recheck
) else (
echo failed to unpack, check your repo 
dir %out%
 exit /b 1
)
:end
