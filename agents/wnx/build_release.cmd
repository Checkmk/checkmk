@echo off
:: File to Build MSI usingMS BUild system
:: Problem based on the fact that we have one x86 Playfrom for MSI
:: but two, x86 and x64, for exe and MSI must have both targets
:: build before owm build start. 
:: this is for command line only
:: In GUI we should do Batch Rebuild of everything
:: variables to set OPTOIONALLY, when you are using the same git checkout multiple times
:: arte - final artefacts, expected bz build script
:: WNX_BUILD - in the future this is name of subfloder to build out
:: creates # artefacts in the output folder

:: 
:: Sign mode:
:: build_release file password
:: file is always in c:\common\store should be well protected from access
::
:: Standard Mode:
:: build_release
::

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
set build_dir=.\build
set SKIP_MINOR_BINARIES=YES

set ExternalCompilerOptions=/DDECREASE_COMPILE_TIME 

if "%1" == "SIMULATE_OK" powershell Write-Host "Successful Build" -Foreground Green && echo aaa > %arte%\check_mk_service.msi  && exit /b 0
if "%1" == "SIMULATE_FAIL" powershell Write-Host "Failed Install build" -Foreground Red && del %arte%\check_mk_service.msi  && exit /b 8

:: CHECK for line ending
@py -3 scripts\check_crlf.py 
@if errorlevel 1 powershell Write-Host "Line Encoding Error`r`n`tPlease check how good repo was checked out" -Foreground Red && exit /b 113

call %cur_dir%\scripts\clean_artifacts.cmd 

call scripts\unpack_packs.cmd

powershell Write-Host "Looking for MSVC 2022..." -Foreground White
set msbuild="C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "Install Visual Studio 2022, please" -Foreground Red && exit /b 8

powershell Write-Host "[+] Found MSVC 2022" -Foreground Green
powershell Write-Host "Building MSI..." -Foreground White
powershell -ExecutionPolicy ByPass -File msb.ps1
if not %errorlevel% == 0 powershell Write-Host "Failed Build" -Foreground Red && exit /b 7

if not "%2" == "" (
powershell Write-Host "Signing Executables" -Foreground White
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe
@call sign_windows_exe c:\common\store\%1 %2 %arte%\cmk-agent-ctl.exe
)

ptime %msbuild% wamain.sln /t:install /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red && exit /b 8

:: Patch Version Phase: Patch version value direct in the msi file
:: set version:
:: remove quotes
echo %wnx_version:~1,-1%
:: info
powershell Write-Host "Setting Version in MSI: %wnx_version%" -Foreground Green
:: command
@echo cscript.exe //nologo WiRunSQL.vbs %arte%\check_mk_agent.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
cscript.exe //nologo scripts\WiRunSQL.vbs %build_dir%\install\Release\check_mk_service.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
:: check result
if not %errorlevel% == 0 powershell Write-Host "Failed version set" -Foreground Red && exit /b 34

goto end
:: Unit Tests Phase: post processing/build special modules using make
:: this phase is skipped, there is no need to inculde unit tests in the build script
powershell Write-Host "starting unit tests" -Foreground Cyan 

pushd %arte%
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

:: Deploy Phase: post processing/build special modules using make
copy %build_dir%\watest\Win32\Release\watest32.exe %arte% /y	
copy %build_dir%\watest\x64\Release\watest64.exe %arte% /Y	
copy %build_dir%\install\Release\check_mk_service.msi %arte%\check_mk_agent.msi /y || powershell Write-Host "Failed to copy msi" -Foreground Red && exit /b 33
copy %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe %arte%\check_mk_agent-64.exe /Y || powershell Write-Host "Failed to create 64 bit agent" -Foreground Red && exit /b 35
copy %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe %arte%\check_mk_agent.exe /Y || powershell Write-Host "Failed to create 32 bit agent" -Foreground Red && exit /b 34
copy install\resources\check_mk.user.yml %arte%
copy install\resources\check_mk.yml %arte%
powershell Write-Host "File Deployment succeeded" -Foreground Green


:: Additional Phase: post processing/build special modules using make
!make_exe! msi_patch || powershell Write-Host "Failed to patch MSI exec" -Foreground Red && echo set && exit /b 36
if not "%2" == "" (
powershell Write-Host "Signing MSI" -Foreground White
copy /Y %arte%\check_mk_agent.msi %arte%\check_mk_agent_no_sign.msi
@call sign_windows_exe c:\common\store\%1 %2 %arte%\check_mk_agent.msi
)



