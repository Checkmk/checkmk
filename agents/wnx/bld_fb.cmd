@echo off
@rem Script to build a frozen binary using pyinstaller
@rem 
@rem requires 32-bit Python(to be compatible with any Windows)
@rem requires upx installed in the choco
@rem %1 file name
@rem %2 optional command line
set p32path=C:\Python27.32

if not exist %p32path% powershell Write-Host "You have to install 32 bit python in directory %p32path%" -Foreground Red && exit /B 1

set PYINSTALLER_CONFIG_DIR=%p32path%\cache
if not exist %PYINSTALLER_CONFIG_DIR% powershell Write-Host "Creating cache %PYINSTALLER_CONFIG_DIR%" -Foreground Green && mkdir %PYINSTALLER_CONFIG_DIR%

if "%1" == "" powershell Write-Host "Usage: bld_fb python_file" -Foreground Yellow && exit /B 1
if not exist "%1" powershell Write-Host "Script %1 not found" -Foreground Red && exit /B 1
powershell Write-Host "Building Script %1 ..." -Foreground Green
set ppath=%p32path%\Scripts
set pupx=C:\ProgramData\chocolatey\bin

@rem The build command itself
@rem echo %ppath%\pyinstaller --clean --onefile --upx-dir="C:\ProgramData\chocolatey\bin" --log-level=INFO %2 %1
%ppath%\pyinstaller --clean --onefile --upx-dir=%pupx% --distpath="build\fb\dist" --workpath="build\fb\work" --specpath="build\fb\spec" --log-level=INFO %2 %1

if not "%errorlevel%"  == "0" powershell Write-Host "Script %1 build is failed" -Foreground Red && exit /B 1
powershell Write-Host "Script %1 build SUCCESS" -Foreground Green