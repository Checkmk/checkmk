@echo off
rem Short Build File

set cur_dir=%cd%
set arte=%cur_dir%\..\..\artefacts
mkdir %arte% 2> nul
mkdir %arte%\plugins 2> nul
mkdir %arte%\watest 2> nul
mkdir %arte%\watest\plugins 2> nul
mkdir %arte%\providers 2> nul
mkdir %arte%\exe 2> nul
mkdir %arte%\pdb 2> nul
set REMOTE_MACHINE=%arte%
set LOCAL_IMAGES_PDB=%arte%\pdb
set LOCAL_IMAGES_EXE=%arte%\exe

powershell Write-Host "Building WATEST with default msbuild..." -Foreground Green
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\MSBuild\15.0\Bin\msbuild.exe"
if exist %msbuild% powershell Write-Host "MSBUILD found" -Foreground Green && goto execute
set msbuild="C:\Program Files (x86)\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\msbuild.exe"
if not exist %msbuild% powershell Write-Host "Install MSBUILD, please" -Foreground Red && exit /b 99
:execute
set exec=watest
%msbuild% wamain.sln /t:%exec% /p:Configuration=Release,Platform=x86
if not %errorlevel% == 0 powershell Write-Host "Failed %exec%-32" -Foreground Red && exit /b 6



