@echo off       
rem check and prepare output folder for smooth deploy and testing
if not "%VS_DEPLOY%" == "YES" goto end
if not exist %REMOTE_MACHINE% echo Error, REMOTE_MACHINE not defined && goto unpack_all
if not exist %LOCAL_IMAGES_EXE% echo Error, LOCAL_IMAGES_EXE not defined && goto unpack_all
if not exist %LOCAL_IMAGES_PDB% echo Error, LOCAL_IMAGES_PDB not defined && goto unpack_all
if not exist %REMOTE_MACHINE%\bin mkdir %REMOTE_MACHINE%\bin
if not exist %REMOTE_MACHINE%\utils mkdir %REMOTE_MACHINE%\utils
if not exist %REMOTE_MACHINE%\plugins mkdir %REMOTE_MACHINE%\plugins
if not exist %REMOTE_MACHINE%\local mkdir %REMOTE_MACHINE%\local
if not exist %REMOTE_MACHINE%\watest mkdir %REMOTE_MACHINE%\watest
:end
