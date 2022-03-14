@echo off
rem Short Build File
rem parameter both build 32 and 64 bit tests

set cur_dir=%cd%
set build_dir=.\build
set arte=%cur_dir%\..\..\artefacts
mkdir %arte% 2> nul

set LOCAL_IMAGES_PDB=%build_dir%
set LOCAL_IMAGES_EXE=%build_dir%

set ExternalCompilerOptions=/DDECREASE_COMPILE_TIME 

powershell Write-Host "Building WATEST with default msbuild..." -Foreground Green
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional\MSBuild\Current\Bin\msbuild.exe"
if exist %msbuild% powershell Write-Host "MSBUILD found" -Foreground Green && goto execute
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "Install MSBUILD, please" -Foreground Red && exit /b 99
:execute
set exec=watest
powershell Write-Host "Building WATEST-32..." -Foreground Green
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if "%errorlevel%" NEQ "0" powershell Write-Host "Failed %exec%-32" -Foreground Red && exit /b 6
if "%1" == "both" powershell Write-Host "Building WATEST-64..." -Foreground Green && %msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86 || powershell Write-Host "Failed %exec%-64" -Foreground Red && exit /b 7
copy "%build_dir%\watest\Win32\Release\watest32.exe" "%arte%" /y	
if "%1" == "both" copy "%build_dir%\watest\x64\Release\watest64.exe" "%arte%" /Y	



