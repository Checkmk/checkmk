@echo off
rem File to Build MSI usingMS BUild system
rem Problem based on the fact that we have one x86 Playfrom for MSI
rem but two, x86 and x64, for exe and MSI must have both targets
rem build before owm build start. 
rem this is for command line only
rem In GUI we should do Batch Rebuild of everything
rem variables to set OPTOIONALLY, when you are using the same git checkout multiple times
rem REMOTE_MACHINE - final artefacts, expected bz build script
rem LOCAL_IMAGES_EXE - exe
rem LOCAL_IMAGE_PDB - pdb
rem WNX_BUILD - in the future this is name of subfloder to build out
rem creates # artefacts in the output folder
SETLOCAL EnableDelayedExpansion

:: CHECK FOR CHOCO
:: if choco is absent then build is not possible(we can't dynamically control environment)
powershell Write-Host "Looking for choco..." -Foreground White
@choco -v > nul
@if "%errorlevel%" NEQ "0" powershell Write-Host "choco must be installed!" -Foreground Red && exit /b 55
powershell Write-Host "[+] choco" -Foreground Green

:: CHECK FOR make
:: if make is absent then we try to install it using choco. Failure meand build fail, make is mandatory
powershell Write-Host "Looking for make..." -Foreground White
for /f %%i in ('where make') do set make_exe=%%i
if "!make_exe!" == "" (
powershell Write-Host "make not found, try to install" -Foreground Yellow 
choco install make -y
for /f %%i in ('where make') do set make_exe=%%i
if "!make_exe!" == "" powershell Write-Host "make not found, something is really bad" -Foreground Red && exit /b 57
)
powershell Write-Host "[+] make" -Foreground Green
 
:: read version from the C++ agent
set /p wnx_version_raw=<src\common\wnx_version.h
:: parse version
set wnx_version=%wnx_version_raw:~30,40%

:: check that version is minimally ok
set wnx_version_mark=%wnx_version_raw:~0,29%
if not "%wnx_version_mark%" == "#define CMK_WIN_AGENT_VERSION" powershell Write-Host "wnx_version.h is invalid" -Foreground Red && exit /b 67
powershell Write-Host "wnx_version.h is ok" -Foreground Green

:: #define CMK_WIN_AGENT_VERSION "

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
set build_dir=.\build

set ExternalCompilerOptions=/DDECREASE_COMPILE_TIME 

if "%1" == "SIMULATE_OK" powershell Write-Host "Successful Build" -Foreground Green && echo aaa > %arte%\check_mk_service.msi  && exit /b 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Failed Install build" -Foreground Red && del %arte%\check_mk_service.msi  && exit /b 8

:: CHECK for line ending
@py -3 check_crlf.py 
@if errorlevel 1 powershell Write-Host "Line Encoding Error`r`n`tPlease check how good repo was checked out" -Foreground Red && exit /b 113

call %cur_dir%\clean_artefacts.cmd 

call scripts\unpack_packs.cmd

powershell Write-Host "Looking for MSVC 2019..." -Foreground White
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "Install Visual Studio 2019, please" -Foreground Red && exit /b 8

powershell Write-Host "[+] Found MSVC 2019" -Foreground Green
powershell Write-Host "Building MSI..." -Foreground White
powershell -ExecutionPolicy ByPass -File msb.ps1
if not %errorlevel% == 0 powershell Write-Host "Failed Build" -Foreground Red && exit /b 7

if not "%2" == "" (
powershell Write-Host "Signing Executables" -Foreground White
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe
)

%msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red && exit /b 8

:: Patch Version Phase: Patch version value direct in the msi file
:: set version:
:: remove quotes
echo %wnx_version:~1,-1%
:: info
powershell Write-Host "Setting Version in MSI: %wnx_version%" -Foreground Green
@rem command
@echo cscript.exe //nologo WiRunSQL.vbs %REMOTE_MACHINE%\check_mk_agent.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
cscript.exe //nologo WiRunSQL.vbs %REMOTE_MACHINE%\check_mk_service.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
@rem check result
if not %errorlevel% == 0 powershell Write-Host "Failed version set" -Foreground Red && exit /b 34

goto end
:: Unit Tests Phase: post processing/build special modules using make
:: this phase is skipped, there is no need to inculde unit tests in the build script
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

@rem Deploy Phase: post processing/build special modules using make
copy install\resources\check_mk.user.yml %REMOTE_MACHINE%
pushd %REMOTE_MACHINE%

copy check_mk_service.msi check_mk_agent.msi || powershell Write-Host "Failed to copy msi" -Foreground Red && exit /b 33
copy check_mk_service32.exe check_mk_agent.exe || powershell Write-Host "Failed to create 32 bit agent" -Foreground Red && exit /b 34
copy check_mk_service64.exe check_mk_agent-64.exe || powershell Write-Host "Failed to create 64 bit agent" -Foreground Red && exit /b 35
powershell Write-Host "File Deployment succeeded" -Foreground Green

popd

copy %build_dir%\watest\Win32\Release\watest32.exe %REMOTE_MACHINE% /y	
copy %build_dir%\watest\x64\Release\watest64.exe %REMOTE_MACHINE% /Y	


:: Additional Phase: post processing/build special modules using make
!make_exe! msi_patch || powershell Write-Host "Failed to patch MSI exec" -Foreground Red && echo set && exit /b 36
if not "%2" == "" (
powershell Write-Host "Signing MSI" -Foreground White
copy /Y %arte%\check_mk_agent.msi %arte%\check_mk_agent_unsigned.msi
:: obfuscate
python ..\..\cmk\utils\obfuscate.py -obfuscate %arte%\check_mk_agent_unsigned.msi %arte%\check_mk_agent_unsigned.msi
@call sign_windows_exe c:\common\store\%1 %2 %arte%\check_mk_agent.msi
)



