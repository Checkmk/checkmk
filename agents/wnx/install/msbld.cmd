@echo off 
set msbuild=%ProgramFiles(x86)%\Microsoft Visual Studio\2017\Professional\MSBuild\15.0\Bin\msBuild.exe
if not exist "%msbuild%" powershell write-host -fore Red  Error: Install Visual Studio 2017 && exit
"%msbuild%" check_mk_vanilla.wixproj
"%msbuild%" check_mk_baked.wixproj
