:: *********************************************
:: Used as a proxy to call any other script to
:: correctly set common environment variables
::
:: 'exec.cmd script PY_VER PY_SUBVER'
::
:: Example: exec.cmd install_legacy.cmd 3.8 7
:: Always return back to current dir
:: *********************************************

@echo off

if "%3" == "" powershell Write-Host "Usage: exec_cmd cmd 3.8 7" -foreground red && exit /b 1
set PY_VER=%2
set PY_SUBVER=%3

:: This is shortcut to fit path in Windows limit of 260 symbols.
set temp=c:\temp

:: Some older Pythons may require this
set MSBUILD="C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\MSBuild.exe"

:: Variables
set p_full_name=python-%PY_VER%.%PY_SUBVER%
set cur_dir=%cd%

:: Points to the doc to build, which may not be build and must be just set to empty file
set chm_368=%cur_dir%\python\%PY_VER%\%p_full_name%\Doc\build\htmlhelp\python368.chm
set chm_dir=%cur_dir%\python\%PY_VER%\%p_full_name%\Doc\build\htmlhelp
set chm_file=%chm_dir%\python38%PY_SUBVER%.chm

:: msiexec doesn't understand relative paths, we have to normalize
call :NORMALIZEPATH "%cur_dir%\..\..\..\omd\packages\Python3\windows\python-3.4.4.msi"
set legacy_msi=%RETVAL%

set my_tmp=%cd%\tmp\%PY_VER%
set build_dir=%my_tmp%\out
set uninstall_dir=%my_tmp%\uninstall
set pexe=%build_dir%\win32\%p_full_name%.exe
set pexe_uninstall=%uninstall_dir%\%p_full_name%.exe
set install_dir=%my_tmp%\to_install
set save_dir=%my_tmp%\to_save
set build_msi=python\%PY_VER%\%p_full_name%\Tools\msi
call %1 
if %errorlevel% EQU 0 (
cd %cur_dir% 
exit /b 0
) Else ( 
cd %cur_dir%
exit /b 1
)


:: ========== FUNCTIONS ==========
:NORMALIZEPATH
  set retval=%~f1
  exit /B