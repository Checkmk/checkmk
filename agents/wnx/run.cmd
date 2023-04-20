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
:: run --all --sign file password
:: file is always in c:\common\store should be well protected from access
::
:: Standard Mode:
:: run --all
::

SETLOCAL EnableDelayedExpansion

if "%*" == "" (
echo: Run default...
set arg_all=1
) else (
:CheckOpts
if "%~1"=="-h" goto Usage
if "%~1"=="--help" goto Usage
if "%~1"=="-?" goto Usage

if "%~1"=="-A"              (set arg_all=1)          & shift & goto CheckOpts
if "%~1"=="--all"           (set arg_all=1)          & shift & goto CheckOpts

if "%~1"=="-c"              (set arg_clean=1)        & shift & goto CheckOpts
if "%~1"=="--clean"         (set arg_clean=1)        & shift & goto CheckOpts

if "%~1"=="-S"              (set arg_setup=1)        & shift & goto CheckOpts
if "%~1"=="--setup"         (set arg_setup=1)        & shift & goto CheckOpts

if "%~1"=="-f"              (set arg_format=1)       & shift & goto CheckOpts
if "%~1"=="--format"        (set arg_format=1)       & shift & goto CheckOpts

if "%~1"=="-F"              (set arg_check_format=1) & shift & goto CheckOpts
if "%~1"=="--check-format"  (set arg_check_format=1) & shift & goto CheckOpts

if "%~1"=="-C"              (set arg_ctl=1)          & shift & goto CheckOpts
if "%~1"=="--controller"    (set arg_ctl=1)          & shift & goto CheckOpts

if "%~1"=="-B"              (set arg_build=1)        & shift & goto CheckOpts
if "%~1"=="--build"         (set arg_build=1)        & shift & goto CheckOpts

if "%~1"=="-M"              (set arg_msi=1)          & shift & goto CheckOpts
if "%~1"=="--msi"           (set arg_msi=1)          & shift & goto CheckOpts

if "%~1"=="-O"              (set arg_ohm=1)          & shift & goto CheckOpts
if "%~1"=="--ohm"           (set arg_ohm=1)          & shift & goto CheckOpts

if "%~1"=="-T"              (set arg_test=1)         & shift & goto CheckOpts
if "%~1"=="--test"          (set arg_test=1)         & shift & goto CheckOpts

if "%~1"=="-D"              (set arg_doc=1)          & shift & goto CheckOpts
if "%~1"=="--documentation" (set arg_doc=1)          & shift & goto CheckOpts

if "%~1"=="--sign"          (set arg_sign_file=%1) & (set arg_sign_secret=%2)   & (set arg_sign=1) & shift & shift & shift goto CheckOpts
)
if "%arg_all%"=="1" (set arg_ctl=1) & (set arg_build=1) & (set arg_test=1) & (set arg_setup=1) & (set arg_ohm=1) & (set arg_msi=1)



@echo logonserver: "%LOGONSERVER%" user: "%USERNAME%"

::Get start time:
for /F "tokens=1-4 delims=:.," %%a in ("%time%") do (
   set /A "start=(((%%a*60)+1%%b %% 100)*60+1%%c %% 100)*100+1%%d %% 100"
)

:: arg_setup
call :check_choco
call :check_make
call :check_repo_crlf
call :check_msvc

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
set build_dir=.\build
set SKIP_MINOR_BINARIES=YES
set ExternalCompilerOptions=/DDECREASE_COMPILE_TIME

:: arg_clean
call :clean

:: arg_build
call :set_wnx_version
if "%arg_build%" == "1" call %cur_dir%\scripts\clean_artifacts.cmd
if "%arg_build%" == "1" call scripts\unpack_packs.cmd
if "%arg_build%" == "1" make install_extlibs
call :build_windows_agent

:: arg_test
call :unit_test

:: arg_ctl
call :build_agent_controller

:: arg_ohm
call :build_ohm

:: arg_msi
call :build_msi
call :set_msi_version
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
powershell Write-Host "Elapsed time: %hh%:%mm%:%ss%,%cc%" -Foreground Blue

call :patch_msi_code 
call :sign_msi

exit /b 0

:: CHECK FOR CHOCO
:: if choco is absent then build is not possible(we can't dynamically control environment)
:check_choco
if not "%arg_setup%" == "1" powershell Write-Host "Skipped setup check" -Foreground Yellow & goto :eof
powershell Write-Host "Looking for choco..." -Foreground White
@choco -v > nul
@if "%errorlevel%" NEQ "0" powershell Write-Host "choco must be installed!" -Foreground Red & call :halt 55
powershell Write-Host "[+] choco" -Foreground Green
goto :eof


:: CHECK FOR make
:: if make is absent then we try to install it using choco. Failure meand build fail, make is mandatory
:check_make
if not "%arg_setup%" == "1" goto :eof
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

:: CHECK for line ending
:check_repo_crlf
if not "%arg_setup%" == "1" goto :eof
@py -3 scripts\check_crlf.py
@if errorlevel 1 powershell Write-Host "Line Encoding Error`r`n`tPlease check how good repo was checked out" -Foreground Red & call :halt 113
goto :eof


:: CHECK for MSVC
:check_msvc
if not "%arg_setup%" == "1" goto :eof
powershell Write-Host "Looking for MSVC 2022..." -Foreground White
set msbuild=C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe
if not exist "%msbuild%" powershell Write-Host "Install Visual Studio 2022, please" -Foreground Red & call :halt 8
powershell Write-Host "[+] Found MSVC 2022" -Foreground Green
goto :eof

:: clean artifacts
:clean
if not "%arg_clean%" == "1" powershell Write-Host "Skipped clean"  & goto :eof
powershell Write-Host "Cleaning..." -Foreground White
if "%arte%" == "" powershell Write-Host "arte is not defined" -Foreground Red & call :halt 99
del /Q %arte%\*.msi > nul
del /Q %arte%\*.exe > nul
del /Q %arte%\*.yml > nul
del /Q %arte%\*.log > nul
del /Q %arte%\*.log > nul
powershell Write-Host "Done." -Foreground Green
goto :eof

:set_wnx_version
if not "%arg_build%" == "1" goto :eof
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


:build_windows_agent
if not "%arg_build%" == "1" powershell Write-Host "Skipped Agent Build" -Foreground Yellow & goto :eof
powershell Write-Host "Building Windows Agent..." -Foreground White
for /f %%i in ('where make') do set make_exe=%%i
powershell -ExecutionPolicy ByPass -File msb.ps1
if errorlevel 1 powershell Write-Host "Failed Build" -Foreground Red & call :halt 7
goto :eof

:build_agent_controller
if not "%arg_ctl%" == "1" powershell Write-Host "Skipped Controller Build" -Foreground Yellow & goto :eof
pushd ..\..\packages\cmk-agent-ctl
call run.cmd --all
if not %errorlevel% == 0 powershell Write-Host "Failed Cargo Build" -Foreground Red && popd & call :halt 72
popd
goto :eof

:build_ohm
if not "%arg_ohm%" == "1" powershell Write-Host "Skipped OHM Build" -Foreground Yellow & goto :eof
call build_ohm.cmd
if not %errorlevel% == 0 powershell Write-Host "Failed OHM Build" -Foreground Red & call :halt 71
goto :eof

:build_msi
if not "%arg_msi%" == "1" powershell Write-Host "Skipped MSI Build" -Foreground Yellow & goto :eof
ptime "%msbuild%" wamain.sln /t:install /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed Install build" -Foreground Red & call :halt 8
goto :eof

:: Patch Version Phase: Patch version value direct in the msi file
:: set version:
:: remove quotes
:set_msi_version
if not "%arg_msi%" == "1" goto :eof
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
if not "%arg_test%" == "1" powershell Write-Host "Skipped Unit test" -Foreground Yellow & goto :eof
net stop WinRing0_1_2_0
copy %build_dir%\watest\Win32\Release\watest32.exe %arte% /Y
copy %build_dir%\watest\x64\Release\watest64.exe %arte% /Y
powershell Write-Host "starting unit tests" -Foreground Cyan
call call_unit_tests.cmd -*_Simulation:*Component:*ComponentExt:*Flaky
if not %errorlevel% == 0 powershell Write-Host "Failed Unit Test" -Foreground Red & call :halt 100
powershell Write-Host "Unit test SUCCESS" -Foreground Green
goto :eof

:sign_binaries
if not "%arg_sign%" == "1" powershell Write-Host "Signing binaries skipped" -Foreground Yellow & goto :eof
powershell Write-Host "Signing Executables" -Foreground White
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\x64\Release\check_mk_service64.exe
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\check_mk_service\Win32\Release\check_mk_service32.exe
@call sign_windows_exe c:\common\store\%1 %2 %arte%\cmk-agent-ctl.exe
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\ohm\OpenHardwareMonitorLib.dll
@call sign_windows_exe c:\common\store\%1 %2 %build_dir%\ohm\OpenHardwareMonitorCLI.exe

goto :eof


:: Deploy Phase: post processing/build special modules using make
:deploy_to_artifacts
if not "%arg_msi%" == "1" goto :eof
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
if not "%arg_msi%" == "1"  goto :eof
!make_exe! msi_patch 
if errorlevel 1 powershell Write-Host "Failed to patch MSI exec" -Foreground Red & call :halt 36
copy /Y %arte%\check_mk_agent.msi %arte%\check_mk_agent_unsigned.msi > nul
goto :eof

:sign_msi
if not "%arg_sign%" == "1" powershell Write-Host "Signing MSI skipped" -Foreground Yellow & goto :eof
powershell Write-Host "Signing MSI" -Foreground White
@call sign_windows_exe c:\common\store\%arg_sign_file% %arg_sign_secret% %arte%\check_mk_agent.msi
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

:Usage
echo.
echo.Usage:
echo.
echo.%~nx0 [arguments]
echo.
echo.Available arguments:
echo.  -?, -h, --help       display help and exit
echo.  -A, --all            shortcut to -S -B -C -T -M:  setup, build, ctl, ohm, unit, msi
echo.  -c, --clean          clean artifacts
echo.  -S, --setup          check setup
echo.  -C, --ctl            build controller
echo.  -D, --documentation  create documentation
echo.  -f, --format         format sources
echo.  -F, --check-format   check for correct formatting
echo.  -B, --build          build controller
echo.  -M, --msi            build msi
echo.  -O, --ohm            build ohm
echo.  -T, --test           run unit test controller
echo.  --sign file secret   sign controller with file in c:\common and secret
echo.
echo.Examples:
echo.
echo %~nx0 --ctl
echo %~nx0 --build --test
echo %~nx0 --build -T --sign the_file secret
echo %~nx0 -A
GOTO :EOF
