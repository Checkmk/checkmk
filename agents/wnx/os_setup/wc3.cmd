@rem
@rem MAIN WINDOWS SETUP SCRIPT
@rem To get special packages as vcpkg
@rem
@rem "vcpkg"
@echo off
SETLOCAL EnableDelayedExpansion

set VCPKG_ROOT=c:\dev\tools\vcpkg
mkdir %VCPKG_ROOT%
cd %VCPKG_ROOT%\..
git clone https://github.com/microsoft/vcpkg
call .\vcpkg\bootstrap-vcpkg.bat
call .\vcpkg\vcpkg install protobuf:x64-windows
call .\vcpkg\vcpkg install protobuf:x86-windows
del /Q /S %VCPKG_ROOT%\buildtrees\protobuf\x64-windows-dbg > nul 
del /Q /S %VCPKG_ROOT%\buildtrees\protobuf\x64-windows-rel > nul
del /Q /S %VCPKG_ROOT%\buildtrees\protobuf\x86-windows-dbg > nul
del /Q /S %VCPKG_ROOT%\buildtrees\protobuf\x86-windows-rel > nul

