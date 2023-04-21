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

@echo logonserver: "%LOGONSERVER%" user: "%USERNAME%"

::Get start time:
for /F "tokens=1-4 delims=:.," %%a in ("%time%") do (
   set /A "start=(((%%a*60)+1%%b %% 100)*60+1%%c %% 100)*100+1%%d %% 100"
)

call :check_choco
call :check_make
call :set_wnx_version
call :check_repo_crlf
call :check_msvc
set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
set build_dir=.\build
set SKIP_MINOR_BINARIES=YES
set ExternalCompilerOptions=/DDECREASE_COMPILE_TIME

call %cur_dir%\scripts\clean_artifacts.cmd
call scripts\unpack_packs.cmd
make install_extlibs

call :build_windows_agent
call :build_agent_controller

call :build_ohm
call :build_msi
call :set_msi_version
call :unit_test
call :sign_binaries
call :deploy_to_artifacts

::Get end time:
for /F "tokens=1-4 delims=:.," %%a in ("%time%") do (
   set /A "end=(((%%a*60)+1%%b %% 100)*60+1%%c %% 100)*100+1%%d %% 100"
)

:: Get elapsed time:
set /A elapsed=end-start

:: Show elapsed time:
set /A hh=elapsed/(60*60*100), rest=elapsed%%(60*60*100), mm=rest/(60*100), rest%%=60*100, ss=rest/100, cc=rest%%100
if %mm% lss 10 set mm=0%mm%
if %ss% lss 10 set ss=0%ss%
if %cc% lss 10 set cc=0%cc%
powershell Write-Host "Elapsed time: %hh%:%mm%:%ss%,%cc%" -Foreground Yellow

call :patch_msi_code 
call :sign_msi %1 %2

exit /b 0

:: CHECK FOR CHOCO
:: if choco is absent then build is not possible(we can't dynamically control environment)
:check_choco
powershell Write-Host "Looking for choco..." -Foreground White
@choco -v > nul
@if "%errorlevel%" NEQ "0" powershell Write-Host "choco must be installed!" -Foreground Red & call :halt 55
powershell Write-Host "[+] choco" -Foreground Green
goto :eof


:: CHECK FOR make
:: if make is absent then we try to install it using choco. Failure meand build fail, make is mandatory
:check_make
powershell Write-Host "Looking for make..." -Foreground White
for /f %%i in ('where make') do set make_exe=%%i
if "!make_exe!" == "" (
powershell Write-Host "make not found, try to install" -Foreground Yellow
choco install make -y
for /f %%i in ('where make') do set make_exe=%%i
if "!make_exe!" == "" powershell Write-Host "make not found, something is really bad" -Foreground Red & call :halt 57
)
powershell Write-Host "[+] make" -Foreground Green
goto :eof

:set_wnx_version
:: read version from the C++ agent
set /p wnx_version_raw=<src\common\wnx_version.h
:: parse version
set wnx_version=%wnx_version_raw:~30,60%

:: check that version is minimally ok
set wnx_version_mark=%wnx_version_raw:~0,29%
if not "%wnx_version_mark%" == "#define CMK_WIN_AGENT_VERSION" powershell Write-Host "wnx_version.h is invalid" -Foreground Red & call :halt 67
powershell Write-Host "wnx_version.h is ok" -Foreground Green
:: #define CMK_WIN_AGENT_VERSION "
goto :eof


:: CHECK for line ending
:check_repo_crlf
@py -3 scripts\check_crlf.py
@if errorlevel 1 powershell Write-Host "Line Encoding Error`r`n`tPlease check how good repo was checked out" -Foreground Red & call :halt 113
goto :eof


:: CHECK for line ending
:check_msvc
powershell Write-Host "Looking for MSVC 2022..." -Foreground White
set msbuild=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe
if not exist "%msbuild%" powershell Write-Host "Install Visual Studio 2022, please" -Foreground Red & call :halt 8
powershell Write-Host "[+] Found MSVC 2022" -Foreground Green
goto :eof

:build_windows_agent
powershell Write-Host "Building Windows Agent..." -Foreground White
powershell -ExecutionPolicy ByPass -File msb.ps1
if errorlevel 1 powershell Write-Host "Failed Build" -Foreground Red & call :halt 7
goto :eof

:build_agent_controller
pushd ..\..\packages\cmk-agent-ctl
call run.cmd --all
if not %errorlevel% == 0 powershell Write-Host "Failed Cargo Build" -Foreground Red && popd & call :halt 72
popd
goto :eof

:build_ohm
call build_ohm.cmd
if not %errorlevel% == 0 powershell Write-Host "Failed OHM Build" -Foreground Red & call :halt 71
goto :eof

:build_msi
ptime "%msbuild%" wamain.sln /t:install /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red & call :halt 8
goto :eof

:: Patch Version Phase: Patch version value direct in the msi file
:: set version:
:: remove quotes
:set_msi_version
echo %wnx_version:~1,-1%
:: info
powershell Write-Host "Setting Version in MSI: %wnx_version%" -Foreground Green
:: command
@echo cscript.exe //nologo WiRunSQL.vbs %arte%\check_mk_agent.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
cscript.exe //nologo scripts\WiRunSQL.vbs %build_dir%\install\Release\check_mk_service.msi "UPDATE `Property` SET `Property`.`Value`='%wnx_version:~1,-1%' WHERE `Property`.`Property`='ProductVersion'"
:: check result
if not %errorlevel% == 0 powershell Write-Host "Failed version set" -Foreground Red & call :halt 34
goto :eof

:unit_test
:: Unit Tests Phase: post processing/build special modules using make
net stop WinRing0_1_2_0
copy %build_dir%\watest\Win32\Release\watest32.exe %arte% /Y
copy %build_dir%\watest\x64\Release\watest64.exe %arte% /Y
powershell Write-Host "starting unit tests" -Foreground Cyan
call call_unit_tests.cmd -*_Long:*Integration:*IntegrationExt
if not %errorlevel% == 0 powershell Write-Host "Failed Unit Test" -Foreground Red & call :halt 100
powershell Write-Host "Unit test SUCCESS" -Foreground Green
goto :eof

:sign_binaries
if not "%2" == "" (
powershell Write-Host "Signing Executables" -Foreground White
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe
@call sign_windows_exe c:\common\store\%1 %2 %arte%\cmk-agent-ctl.exe
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\ohm\OpenHardwareMonitorLib.dll
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\ohm\OpenHardwareMonitorCLI.exe
)
goto :eof


:: Deploy Phase: post processing/build special modules using make
:deploy_to_artifacts
copy %build_dir%\install\Release\check_mk_service.msi %arte%\check_mk_agent.msi /y || powershell Write-Host "Failed to copy msi" -Foreground Red && exit /b 33
copy %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe %arte%\check_mk_agent-64.exe /Y || powershell Write-Host "Failed to create 64 bit agent" -Foreground Red && exit /b 34
copy %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe %arte%\check_mk_agent.exe /Y || powershell Write-Host "Failed to create 32 bit agent" -Foreground Red && exit /b 35
copy %build_dir%\ohm\OpenHardwareMonitorCLI.exe %arte%\OpenHardwareMonitorCLI.exe /Y || powershell Write-Host "Failed to copy OHM exe" -Foreground Red && exit /b 36
copy %build_dir%\ohm\OpenHardwareMonitorLib.dll %arte%\OpenHardwareMonitorLib.dll /Y || powershell Write-Host "Failed to copy OHM dll" -Foreground Red && exit /b 37
copy install\resources\check_mk.user.yml %arte%
copy install\resources\check_mk.yml %arte%
powershell Write-Host "File Deployment succeeded" -Foreground Green
goto :eof

:: Additional Phase: post processing/build special modules using make
:patch_msi_code
!make_exe! msi_patch 
if errorlevel 1 powershell Write-Host "Failed to patch MSI exec" -Foreground Red & call :halt 36
copy /Y %arte%\check_mk_agent.msi %arte%\check_mk_agent_unsigned.msi > nul
goto :eof

:sign_msi
if "%2" == "" powershell Write-Host "Signing skipped" -Foreground Yellow & goto :eof
powershell Write-Host "Signing MSI" -Foreground White
@call sign_windows_exe c:\common\store\%1 %2 %arte%\check_mk_agent.msi
call scripts\call_signing_tests.cmd 
if errorlevel 1 call powershell Write-Host "Failed MSI signing test %errorlevel%" -Foreground Red & :halt 41
powershell Write-Host "MSI signing succeeded" -Foreground Green
goto :eof


:: Sets the errorlevel and stops the batch immediately
:halt
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