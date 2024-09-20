@echo off
::
:: Script to build/test/sign/deploy
::
:: Prefix worker, standart for NON-COMPOSITE run.cmd
::
:: Similar in functionality with run scripts from packages
::

SETLOCAL EnableDelayedExpansion

if "%*" == "" (
echo: Run default...
set worker_arg_all=1
) else (
:CheckOpts
if "%~1"=="-h" goto Usage
if "%~1"=="-help" goto Usage
if "%~1"=="-?" goto Usage

if not "%worker_var_value%" == "" (
set %worker_var_name%=%worker_var_value%
set worker_var_value=
)

if "%~1"=="-A"              (set worker_arg_all=1)          & shift & goto CheckOpts
if "%~1"=="--all"           (set worker_arg_all=1)          & shift & goto CheckOpts

if "%~1"=="-c"              (set worker_arg_clean=1)        & shift & goto CheckOpts
if "%~1"=="--clean"         (set worker_arg_clean=1)        & shift & goto CheckOpts

if "%~1"=="-f"              (set worker_arg_format=1)       & shift & goto CheckOpts
if "%~1"=="--format"        (set worker_arg_format=1)       & shift & goto CheckOpts

if "%~1"=="-F"              (set worker_arg_check_format=1) & shift & goto CheckOpts
if "%~1"=="--check-format"  (set worker_arg_check_format=1) & shift & goto CheckOpts

if "%~1"=="-C"              (set worker_arg_clippy=1)       & shift & goto CheckOpts
if "%~1"=="--clippy"        (set worker_arg_clippy=1)       & shift & goto CheckOpts

if "%~1"=="-B"              (set worker_arg_build=1)        & shift & goto CheckOpts
if "%~1"=="--build"         (set worker_arg_build=1)        & shift & goto CheckOpts

if "%~1"=="-T"              (set worker_arg_test=1)         & shift & goto CheckOpts
if "%~1"=="--test"          (set worker_arg_test=1)         & shift & goto CheckOpts

if "%~1"=="-D"              (set worker_arg_doc=1)          & shift & goto CheckOpts
if "%~1"=="--documentation" (set worker_arg_doc=1)          & shift & goto CheckOpts

if "%~1"=="--var"           (set worker_var_name=%~2) & (set worker_var_value=%~3)   & shift & shift & shift & goto CheckOpts

if "%~1"=="--sign"          (set worker_arg_sign_file=%~2) & (set worker_arg_sign_secret=%~3)   & (set worker_arg_sign=1) & shift & shift & shift goto CheckOpts
)
if "%worker_arg_all%"=="1" (set worker_arg_clippy=1) & (set worker_arg_build=1) & (set worker_arg_test=1) & (set worker_arg_check_format=1)

:: Configure environment variables
set worker_cur_dir=%cd%
call setup_config.cmd
if ERRORLEVEL 1 powershell Write-Host "Failed to configure" -Foreground Red &&  exit /b 99
set worker_arte=%worker_root_dir%\artefacts
mkdir %worker_arte% 2> nul

:: Setup shortcut call for CI(to make names shorter than 255 chars)
set ci_root_dir=workdir\workspace\checkmk\master
set ci_junction_to_root_dir=yy
set script_to_run=.\scripts\cargo_build_core.cmd
powershell -ExecutionPolicy ByPass -File %worker_root_dir%/scripts/windows/shorten_dir_and_call.ps1 %ci_root_dir% %ci_junction_to_root_dir% %script_to_run%
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
echo.  -C, --clippy         run clippy for %worker_name%
echo.  -D, --documentation  create documentation
echo.  -f, --format         format sources
echo.  -F, --check-format   check for correct formatting
echo.  -B, --build          build %worker_name%
echo.  -T, --test           test %worker_name%
echo.  --sign file secret   sign %worker_name% with file and secret
echo.
echo.Examples:
echo.
echo %~nx0 --clippy
echo %~nx0 --build --test
echo %~nx0 --build --test -S mypasswd -C
echo %~nx0 -A
GOTO :EOF
