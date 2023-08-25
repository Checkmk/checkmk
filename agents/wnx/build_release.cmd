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
set usbip_exe=c:\common\usbip-win-0.3.6-dev\usbip.exe

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

:: SIGNING of binaries
if "%2" == "" goto build_msi
powershell Write-Host "Signing Executables" -Foreground White
:: Ensure target win32 is build before signing
%msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red & call :halt 11
call scripts\attach_usb_token.cmd %usbip_exe% yubi-usbserver.lan.checkmk.net 1-1.2 .\scripts\attach.ps1
@call scripts\sign_code.cmd %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe
@call scripts\sign_code.cmd %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe

:: BUILD OF MSI
:build_msi
if "%2" == "" del %build_dir%\install\Release\check_mk_service.msi
%msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red & call :halt 8

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
if not %errorlevel% == 0 powershell Write-Host "Failed version set" -Foreground Red & call :halt 34

@rem Deploy Phase: post processing/build special modules using make
copy install\resources\check_mk.user.yml %REMOTE_MACHINE%
copy %build_dir%\install\Release\check_mk_service.msi %REMOTE_MACHINE%\check_mk_agent.msi /y || ( powershell Write-Host "Failed to copy msi" -Foreground Red & call :halt 33 )
copy %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe %REMOTE_MACHINE%\check_mk_agent.exe /Y || ( powershell Write-Host "Failed to create 64 bit agent" -Foreground Red & call :halt 35 )
copy %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe %REMOTE_MACHINE%\check_mk_agent-64.exe /Y || ( powershell Write-Host "Failed to create 32 bit agent" -Foreground Red & call :halt 34 )
powershell Write-Host "File Deployment succeeded" -Foreground Green

copy %build_dir%\watest\Win32\Release\watest32.exe %REMOTE_MACHINE% /y	
copy %build_dir%\watest\x64\Release\watest64.exe %REMOTE_MACHINE% /Y	


:: Additional Phase: post processing/build special modules using make
!make_exe! msi_patch || ( powershell Write-Host "Failed to patch MSI exec" -Foreground Red && echo set & call :halt 36 )
if "%2" == "" goto skip_msi_signing
powershell Write-Host "Signing MSI" -Foreground White
copy /Y %arte%\check_mk_agent.msi %arte%\check_mk_agent_unsigned.msi
:: obfuscate
python ..\..\cmk\utils\obfuscate.py -obfuscate %arte%\check_mk_agent_unsigned.msi %arte%\check_mk_agent_unsigned.msi
@call scripts\sign_code.cmd %arte%\check_mk_agent.msi
if not %errorlevel% == 0 powershell Write-Host "Failed version set" -Foreground Red & call :halt 45
call scripts\detach_usb_token.cmd %usbip_exe%
:skip_msi_signing
exit /b 0

:: Sets the errorlevel and stops the batch immediately
:halt
call scripts\detach_usb_token.cmd %usbip_exe%
call :__SetErrorLevel %1
call :__ErrorExit 2> nul
goto :eof

:__ErrorExit
rem Creates a syntax error, stops immediately
()
goto :eof

:__SetErrorLevel
exit /b %time:~-2%
goto :eof
