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
set LOCAL_IMAGES_PDB=%arte%\pdb
set LOCAL_IMAGES_EXE=%arte%\exe

if "%1" == "SIMULATE_OK" powershell Write-Host "Successful Build" -Foreground Green && echo aaa > %arte%\check_mk_service.msi  && exit 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Failed Install build" -Foreground Red && del %arte%\check_mk_service.msi  && exit 8

powershell Write-Host "Building MSI..." -Foreground Green
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "MSBUILD not found, trying Visual Professional" -Foreground Yellow && set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "Install MSBUILD, please" -Foreground Red && exit 99

set exec=check_mk_service
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit 1
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-64" -Foreground Red && exit 2

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

set exec=watest
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit 6
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-64" -Foreground Red && exit 7

%msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x64
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red && exit 8
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
del %REMOTE_MACHINE%\check_mk_service.msi
exit 100
:end



