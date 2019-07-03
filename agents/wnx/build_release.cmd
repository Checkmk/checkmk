@echo off
rem File to Build MSI usingMS BUild system
rem Problem based on the fact that we have one x86 Playfrom for MSI
rem but two, x86 and x64, for exe and MSI must have both targets
rem build before owm build start. 
rem this is for command line only
rem In GUI we should do Batch Rebuild of everything
rem variables to set OPTOIONALLY, when you are using the same git checkout multiple times
rem REMOTE_MACHINE - final artefacts
rem LOCAL_IMAGES_EXE - exe
rem LOCAL_IMAGE_PDB - pdb
rem WNX_BUILD - in the future this is name of subfloder to build out
rem creates # artefacts in the output folder
SETLOCAL EnableDelayedExpansion

rem read version from the C++ agent
set /p wnx_version_raw=<src\common\wnx_version.h
rem parse version
set wnx_version=%wnx_version_raw:~30,40%

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
mkdir %arte% 2> nul
mkdir %arte%\plugins 2> nul
mkdir %arte%\watest 2> nul
mkdir %arte%\watest\plugins 2> nul
mkdir %arte%\providers 2> nul
mkdir %arte%\exe 2> nul
mkdir %arte%\pdb 2> nul
set REMOTE_MACHINE=%arte%
set VS_DEPLOY=YES
set VS_DEPLOY_MSI=YES
set LOCAL_IMAGES_PDB=%arte%\pdb
set LOCAL_IMAGES_EXE=%arte%\exe
set SKIP_MINOR_BINARIES=YES

if "%1" == "SIMULATE_OK" powershell Write-Host "Successful Build" -Foreground Green && echo aaa > %arte%\check_mk_service.msi  && exit 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Failed Install build" -Foreground Red && del %arte%\check_mk_service.msi  && exit 8

call %cur_dir%\clean_artefacts.cmd 

powershell Write-Host "Building MSI..." -Foreground Green
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "MSBUILD not found, trying Visual Professional" -Foreground Yellow && set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "Install MSBUILD, please" -Foreground Red && exit 99

set exec=check_mk_service
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit 1
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-64" -Foreground Red && exit 2

goto build_watest
if "%SKIP_MINOR_BINARIES%" == "YES" powershell Write-Host "Skipping Minor Binaries!!!!" -Foreground Green goto build_watest
set exec=plugin_player
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit 2
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-64" -Foreground Red && exit 3

set exec=providers\perf_counter
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit 4
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-64" -Foreground Red && exit 5


:build_watest
set exec=watest
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit 6
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-64" -Foreground Red && exit 7

@rem auto install msi
git update-index --assume-unchanged install/resources/check_mk.marker > nul
@copy install\resources\check_mk.marker save.tmp > nul
echo update > install\resources\check_mk.marker
%msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x64
set el=%errorlevel%
@type save.tmp > install\resources\check_mk.marker
@del save.tmp > nul
git update-index --no-assume-unchanged install/resources/check_mk.marker > nul
if not %el% == 0 powershell Write-Host "Failed Install build" -Foreground Red && exit 88
rem move %REMOTE_MACHINE%\check_mk_service.msi %REMOTE_MACHINE%\check_mk_agent_update.msi


%msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red && exit 8

rem set version:
rem remove quotes
echo %wnx_version:~1,-1%
rem info
powershell Write-Host "Setting Version in MSI: %wnx_version%" -Foreground Green
rem command
echo cscript.exe //nologo WiRunSQL.vbs %REMOTE_MACHINE%\check_mk_agent.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
cscript.exe //nologo WiRunSQL.vbs %REMOTE_MACHINE%\check_mk_service.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
rem check result
if not %errorlevel% == 0 powershell Write-Host "Failed version set" -Foreground Red && exit 34

goto end
@rem ignored:
powershell Write-Host "starting unit tests" -Foreground Cyan 

pushd %REMOTE_MACHINE%
watest
if not %errorlevel% == 0 goto error
popd
powershell Write-Host "Unit test SUCCESS" -Foreground Green

:error
popd
powershell Write-Host "Unit test failed" -Foreground Red 
powershell Write-Host "Killing msi in artefacts" -Foreground Red 
call %cur_dir%\clean_artefacts.cmd 
exit 100
:end
copy install\resources\check_mk.user.yml %REMOTE_MACHINE%
pushd %REMOTE_MACHINE%

copy check_mk_service.msi check_mk_agent.msi || powershell Write-Host "Failed to copy msi" -Foreground Red && exit 33
copy check_mk_service32.exe check_mk_agent.exe || powershell Write-Host "Failed to create 32 bit agent" -Foreground Red && exit 34
copy check_mk_service64.exe check_mk_agent-64.exe || powershell Write-Host "Failed to create 64 bit agent" -Foreground Red && exit 35
powershell Write-Host "File Deployment succeeded" -Foreground Green

rem touching update msi
rem copy check_mk_agent_update.msi /B+ ,,/Y > nul
popd


