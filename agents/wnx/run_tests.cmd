@echo off
:: To execute all complicated tests of windows agent
:: params regression, component, ext, simulation, integration, all
::
:: CI must run regression, component, integration, all
:: Dev machine must run also ext and simulation
:: later tests may require some additional package installed which ae not suitable for CI VM
SETLOCAL EnableDelayedExpansion

if "%*" == "" (
echo: Run default...
set int_arg_component=1
set int_arg_ext=
set int_arg_simulation=
set int_arg_integration=
set int_arg_regression=
set int_arg_plugins=
) else (
:CheckOpts
if "%~1"=="-h" goto Usage
if "%~1"=="--help" goto Usage
if "%~1"=="-?" goto Usage

if "%~1"=="-A"              (set int_arg_all=1)           & shift & goto CheckOpts
if "%~1"=="--all"           (set int_arg_all=1)           & shift & goto CheckOpts

if "%~1"=="-C"              (set int_arg_component=1)     & (set int_arg_build=1)     & shift & goto CheckOpts
if "%~1"=="--component"     (set int_arg_component=1)     & (set int_arg_build=1)     & shift & goto CheckOpts

if "%~1"=="-E"              (set int_arg_ext=1)           & (set int_arg_build=1)     & shift & goto CheckOpts
if "%~1"=="--ext"           (set int_arg_ext=1)           & (set int_arg_build=1)     & shift & goto CheckOpts

if "%~1"=="-S"              (set int_arg_simulation=1)    & (set int_arg_build=1)     & shift & goto CheckOpts
if "%~1"=="--simulation"    (set int_arg_simulation=1)    & (set int_arg_build=1)     & shift & goto CheckOpts

if "%~1"=="-I"              (set int_arg_integration=1)   & (set int_arg_build=1)     & shift & goto CheckOpts
if "%~1"=="--integration"   (set int_arg_integration=1)   & (set int_arg_build=1)     & shift & goto CheckOpts

if "%~1"=="-P"              (set int_arg_plugins=1)       & shift & goto CheckOpts
if "%~1"=="--plugins"       (set int_arg_plugins=1)       & shift & goto CheckOpts

if "%~1"=="-R"              (set int_arg_regression=1)    & shift & goto CheckOpts
if "%~1"=="--regression"    (set int_arg_regression=1)    & shift & goto CheckOpts

)
if "%int_arg_all%"=="1" (
set int_arg_component=1
set int_arg_ext=1
set int_arg_simulation=1
set int_arg_integration=1
set int_arg_regression=1
set int_arg_plugins=1
)

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
set CHECKMK_GIT_DIR=%cur_dir%\..\..\


call :watest_build
call :component
call :ext
call :simulation
call :regression
call :integration
call :plugins
goto :end

goto :end



:watest_build
if not "%int_arg_build%" == "1" powershell Write-Host "Skipped build watest" -Foreground Yellow & goto :eof
call scripts\unpack_packs.cmd
make install_extlibs || ( powershell Write-Host "Failed to install packages" -Foreground Red & call :halt 33 )
call build_watest.cmd
if errorlevel 1 powershell write-Host "Build watest FAIL!" -Foreground Red & call :halt 19
powershell write-Host "Build watest SUCCESS!" -Foreground Green
goto :eof


:component
if not "%int_arg_component%" == "1" powershell Write-Host "Skipped component tests" -Foreground Yellow & goto :eof
call call_unit_tests.cmd *Component 
if errorlevel 1 powershell write-Host "Component FAIL!" -Foreground Red & call :halt 20
powershell write-Host "Component SUCCESS!" -Foreground Green
goto :eof


:ext
if not "%int_arg_ext%" == "1" powershell Write-Host "Skipped ext tests" -Foreground Yellow & goto :eof
call call_unit_tests.cmd *ComponentExt
if errorlevel 1 powershell write-Host "Ext FAIL!" -Foreground Red & call :halt 21
powershell write-Host "Ext SUCCESS!" -Foreground Green
goto :eof

:simulation
if not "%int_arg_simulation%" == "1" powershell Write-Host "Skipped simulation tests" -Foreground Yellow & goto :eof
call call_unit_tests.cmd *_Simulation
if errorlevel 1 powershell write-Host "Simulation FAIL!" -Foreground Red & call :halt 21
powershell write-Host "Simulation SUCCESS!" -Foreground Green
goto :eof

:regression
if not "%int_arg_regression%" == "1" powershell Write-Host "Skipped regression tests" -Foreground Yellow & goto :eof
call scripts\call_regression_tests.cmd
if errorlevel 1 powershell write-Host "Regression FAIL!" -Foreground Red & call :halt 21
powershell write-Host "Regression SUCCESS!" -Foreground Green
goto :eof


:integration
if not "%int_arg_integration%" == "1" powershell Write-Host "Skipped integration tests" -Foreground Yellow & goto :eof
call scripts\call_integration_tests.cmd
if errorlevel 1 powershell write-Host "integration FAIL!" -Foreground Red & call :halt 21
powershell write-Host "integration SUCCESS!" -Foreground Green
goto :eof


:plugins
if not "%int_arg_plugins%" == "1" powershell Write-Host "Skipped plugins tests" -Foreground Yellow & goto :eof
call scripts\call_ap_tests.cmd
if errorlevel 1 powershell write-Host "plugins FAIL!" -Foreground Red & call :halt 21
powershell write-Host "plugins SUCCESS!" -Foreground Green
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

:end
exit /b 0
goto :eof

:Usage
echo.
echo.Usage:
echo.
echo.%~nx0 [arguments]
echo.
echo.Available arguments:
echo.  -?, -h, --help       display help and exit
echo.  -A, --all            run all possible tests
echo.  -C, --component      component tests(marked with Component suffix )
echo.  -E, --ext            extended component tests(marked with ComponentExt suffix )
echo.  -S, --simulation     simulation tests(marked with _Simulation suffix )
echo.  -I, --integration    integration tests
echo.  -D, --regression     regression tests
echo.  -f, --plugins        agent plugins test
echo.
echo.Examples:
echo.
echo %~nx0 --component
echo %~nx0 -R -I
echo %~nx0 -A
GOTO :EOF
