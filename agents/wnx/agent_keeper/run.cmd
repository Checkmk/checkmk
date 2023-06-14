@echo off
::
:: Script to build/test/sign/deploy windows agent keeper
::  
:: Similar in functionality with run scripts from packages
::

SETLOCAL EnableDelayedExpansion

if "%*" == "" (
echo: Run default...
set keep_arg_all=1
) else (
:CheckOpts
if "%~1"=="-h" goto Usage
if "%~1"=="-help" goto Usage
if "%~1"=="-?" goto Usage

if "%~1"=="-A"              (set keep_arg_all=1)          & shift & goto CheckOpts
if "%~1"=="--all"           (set keep_arg_all=1)          & shift & goto CheckOpts

if "%~1"=="-c"              (set keep_arg_clean=1)        & shift & goto CheckOpts
if "%~1"=="--clean"         (set keep_arg_clean=1)        & shift & goto CheckOpts

if "%~1"=="-f"              (set keep_arg_format=1)       & shift & goto CheckOpts
if "%~1"=="--format"        (set keep_arg_format=1)       & shift & goto CheckOpts

if "%~1"=="-F"              (set keep_arg_check_format=1) & shift & goto CheckOpts
if "%~1"=="--check-format"  (set keep_arg_check_format=1) & shift & goto CheckOpts

if "%~1"=="-C"              (set keep_arg_clippy=1)       & shift & goto CheckOpts
if "%~1"=="--clippy"        (set keep_arg_clippy=1)       & shift & goto CheckOpts

if "%~1"=="-B"              (set keep_arg_build=1)        & shift & goto CheckOpts
if "%~1"=="--build"         (set keep_arg_build=1)        & shift & goto CheckOpts

if "%~1"=="-T"              (set keep_arg_test=1)         & shift & goto CheckOpts
if "%~1"=="--test"          (set keep_arg_test=1)         & shift & goto CheckOpts

if "%~1"=="-D"              (set keep_arg_doc=1)          & shift & goto CheckOpts
if "%~1"=="--documentation" (set keep_arg_doc=1)          & shift & goto CheckOpts

if "%~1"=="--sign"          (set keep_arg_sign_file=%1) & (set keep_arg_sign_secret=%2)   & (set keep_arg_sign=1) & shift & shift & shift goto CheckOpts
)
if "%keep_arg_all%"=="1" (set keep_arg_clippy=1) & (set keep_arg_build=1) & (set keep_arg_test=1) & (set keep_arg_check_format=1)

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
echo.  -A, --all            shortcut to -F -C -B -T:  check format, clippy, build and test
echo.  -c, --clean          clean artifacts
echo.  -C, --clippy         run clippy for controller
echo.  -D, --documentation  create documentation
echo.  -f, --format         format sources
echo.  -F, --check-format   check for correct formatting
echo.  -B, --build          build keeper
echo.  -T, --test           test keeper
echo.  --sign file secret   sign keeper with file and secret
echo.
echo.Examples:
echo.
echo %~nx0 --clippy
echo %~nx0 --build --test
echo %~nx0 --build --test -S mypasswd -C
echo %~nx0 -A
GOTO :EOF
