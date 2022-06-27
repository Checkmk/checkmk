:: Manually installs required packages because pipfile support in 3.4.4 is "limited"
:: May be called only from exec_cmd.bat

if not defined install_dir powershell Write-Host "Must be called from the exec_cmd.bat, install_dir" -foreground Red && exit /b 3

:: CLEAN
if exist %save_dir% powershell Remove-Item "tmp\3.4\to_save\*" -Force -Recurse
mkdir %save_dir%

cd %install_dir%
:: VENV for "Python 3.4.4"
.\python -m venv %save_dir%\.venv

:: LIBS
xcopy %install_dir%\Lib %save_dir%\Lib /I /E >nul

:: INSTALL mostly from pip file
cd %save_dir%\.venv\Scripts
.\python -m pip install pip==19.1.1
.\python -m pip install --upgrade setuptools
.\python -m pip install colorama==0.4.1
.\python -m pip install pyyaml==5.1.2
.\python -m pip install certifi==2020.4.5.1
.\python -m pip install chardet==3.0.4
.\python -m pip install idna==2.9
.\python -m pip install requests[socks]==2.21.0
.\python -m pip install urllib3==1.24.3
.\python -m pip install cffi==1.13
.\python -m pip install pyopenssl==18.0.0
.\python -m pip install pypiwin32==219
.\python -m pip install typing

cd %cur_dir%
exit /b 0
