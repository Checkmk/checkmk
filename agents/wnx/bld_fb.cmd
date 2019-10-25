@echo off
@rem Script to build frozen binary
@rem %1 file name
@rem @2 optional command line

if "%1" == "" powershell Write-Host "Usage: bld_fb python_file" -Foreground Yellow && exit /B 1
if not exist "%1" powershell Write-Host "Script %1 not found" -Foreground Red && exit /B 1
powershell Write-Host "Building Script %1 ..." -Foreground Green
set ppath=C:\Python27\Scripts
set pupx=C:\ProgramData\chocolatey\bin

@rem The build command itself
echo %ppath%\pyinstaller --clean --onefile --upx-dir="C:\ProgramData\chocolatey\bin" --log-level=INFO %2 %1
%ppath%\pyinstaller --clean --onefile --upx-dir="C:\ProgramData\chocolatey\bin" --distpath="build\fb\dist" --workpath="build\fb\work" --specpath="build\fb\spec" --log-level=ERROR %2 %1

if not "%errorlevel%"  == "0" powershell Write-Host "Script %1 build is failed" -Foreground Red && exit /B 1
powershell Write-Host "Script %1 build SUCCESS" -Foreground Green