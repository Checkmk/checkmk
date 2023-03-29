@echo off
::
:: Script to build/test/sign/deploy windows agent controller
::  
:: Similar in functionality with run scripts from packages
::

if "%*" == "" (
echo: Run default...
set arg_build=1
set arg_clippy=1
set arg_test=1
set arg_sign=
) else (
:CheckOpts
if "%~1"=="-h" goto Usage
if "%~1"=="-help" goto Usage
if "%~1"=="-?" goto Usage
if "%~1"=="-A" (set arg_clippy=1) & (set arg_build=1) & (set arg_test=1) & shift & goto CheckOpts
if "%~1"=="--all" (set arg_clippy=1) & (set arg_build=1) & (set arg_test=1) & shift & goto CheckOpts
if "%~1"=="-C" (set arg_clippy=1) & shift & goto CheckOpts
if "%~1"=="--clippy" (set arg_clippy=1) & shift & goto CheckOpts
if "%~1"=="-B" (set arg_build=1) & shift & goto CheckOpts
if "%~1"=="--build" (set arg_build=1) & shift & goto CheckOpts
if "%~1"=="-T" (set arg_test=1) & shift & goto CheckOpts
if "%~1"=="--test" (set arg_test=1) & shift & goto CheckOpts
if "%~1"=="-S" (set arg_sign=%2) & shift & shift & goto CheckOpts
if "%~1"=="--sign" (set arg_sign=%2) & shift & shift & goto CheckOpts
)

set ci_root_dir=workdir\workspace
set ci_junction_to_root_dir=x
set script_to_run=.\scripts\cargo_build_core.cmd
powershell -ExecutionPolicy ByPass -File scripts/shorten_dir_and_call.ps1 %ci_root_dir% %ci_junction_to_root_dir% %script_to_run%
GOTO :EOF



:Usage
echo.
echo.Usage:
echo.
echo.%~nx0 [arguments]
echo.
echo.Available arguments:
echo.  -?, -h, --help       display help and exit
echo.  -A, --all            run clippy, build and test
echo.  -C, --clippy         run clippy for controller
echo.  -B, --build          build controller
echo.  -T, --test           test controller
echo.  -S, --sign password  sign controller with password
echo.
echo.Examples:
echo.
echo %~nx0 --clippy
echo %~nx0 --build --test
echo %~nx0 --build --test -S mypasswd -C
echo %~nx0 -A
GOTO :EOF
