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
set first=1
:recheck
if not exist ..\..\extlibs echo "no extlibs" && goto install
if not exist ..\..\extlibs\googletest echo "no googletest" &&  goto install
if not exist ..\..\extlibs\simpleini echo "no simpleini" && goto install
if not exist ..\..\extlibs\asio echo "no asio" && goto install
if not exist ..\..\extlibs\catch2 echo "no catch2" && goto install
if not exist ..\..\extlibs\fmt echo "no fmt" && goto install
if not exist ..\..\extlibs\json echo "no json" && goto install
if not exist ..\..\extlibs\yaml-cpp echo "no yaml-cpp" && goto install
if not exist ..\..\extlibs\asio\include\asio.hpp "no asio.hpp" && goto install
echo package check success
goto end
:install
if "%first%" == "1" (
echo try to unpack
call ..\..\..\windows\dependencies\unpack_all.cmd ..\..\..\..\omd\packages ..\..\..\windows\dependencies ..\..\extlibs 
set first=0
goto recheck
) else (
echo failed to unpack, check your repo 
dir ..\..\extlibs
 exit /b 1
)
:end
