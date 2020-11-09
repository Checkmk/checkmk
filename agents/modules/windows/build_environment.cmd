@rem  Python installer script
@rem  May be called only from exec_cmd.bat

rem @echo off
if not defined save_dir powershell Write-Host "This script must be called using exec_cmd" -foreground red && exit /b 2
if not exist %save_dir% powershell Write-Host "`'%save_dir%`' absent" -foreground red && exit /b 4
cd %save_dir%
set PIPENV_VENV_IN_PROJECT=true
set PIPENV_ALWAYS_COPY=true
set PIPENV_NO_INHERIT=true
set PIPENV_DEFAULT_PYTHON_VERSION="%cd%"
set PYTHONPATH=%cd%\Lib\;%cd%\DLLs\
set PYTHONHOME=%cd%
set PATH=%cd%\;%cd%\Scripts\;%PATH%
%cd%\python.exe -m pipenv sync --python=%cd%\python.exe || exit /b 5
