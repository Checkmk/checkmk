:: Builds Python
:: May be called only from exec_cmd.bat

@echo off
if not defined build_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
powershell Write-Host "Making build folder" -foreground Green
mkdir %build_dir% 2> nul
if not exist %build_dir% Write-Host "Failed find tmp folder %build_dir%" -Foreground Red && exit /b 1
powershell Write-Host "Entering %build_msi% folder" -foreground Green
cd %build_msi% 2> nul  || powershell Write-Host "cannot find a python sources" -foreground Red && exit /b 2
powershell Write-Host "Starting build" -foreground Green
set GIT=c:\Program Files\git\cmd\git.exe
set HOST_PYTHON=c:\python38\python.exe
set

@echo call buildrelease.bat  -o %build_dir% -b -x86 --skip-nuget --skip-pgo --skip-zip
if "%PY_VER%" == "3.6" (
  :: 3.6 cant build doc
  powershell Write-Host "Creating empty %chm_368%" -foreground white
  del %chm_368%
  type nul >>%chm_368%
  call buildrelease.bat  -o %build_dir% -b -x86 --skip-nuget --skip-pgo --skip-zip -D
)else (
  powershell Write-Host "Creating dir %chm_dir%" -foreground white
  mkdir %chm_dir% 2> nul
  powershell Write-Host "Creating empty %chm_file%" -foreground white
  del %chm_file%
  type nul >>%chm_file%
  call buildrelease.bat  -o %build_dir% -b -x86 --skip-nuget --skip-pgo --skip-zip -D
)

