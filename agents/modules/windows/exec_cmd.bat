:: *********************************************
:: Used as a proxy to call any other script to
:: correctly set common environment variables
::
:: 'exec.cmd script PY_VER PY_SUBVER'
::
:: Example: exec.cmd install_legacy.cmd 3.12 0
:: Always return back to current dir
:: *********************************************

@echo off

if "%3" == "" powershell Write-Host "Usage: exec_cmd cmd 3.12 0" -foreground red && exit /b 1
set PY_VER=%2
set PY_SUBVER=%3
:: remove dot from the PY_VER
set PY_VER_COMPACT=%PY_VER:.=%

:: This is shortcut to fit path in Windows limit of 260 symbols.
set temp=c:\temp

:: Since 3.11 we could use latest ione
set MSBUILD="C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe"

:: Variables
set p_full_name=python-%PY_VER%.%PY_SUBVER%
set cur_dir=%cd%

:: Points to the doc to build, which may not be build and must be just set to empty file
set chm_368=%cur_dir%\python\%PY_VER%\%p_full_name%\Doc\build\htmlhelp\python368.chm
set chm_dir=%cur_dir%\python\%PY_VER%\%p_full_name%\Doc\build\htmlhelp
set chm_file=%chm_dir%\python%PY_VER_COMPACT%%PY_SUBVER%.chm

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
