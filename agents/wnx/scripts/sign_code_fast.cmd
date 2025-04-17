@echo off
::
:: File to sign code using YK token
::

if "%1" == "" powershell Write-Host "Invalid binary to quick sign" -ForegroundColor Red && goto usage

set pin=469673
set cert=7b97b15df65358623576584b7aafbe04d6668a0e
c:\common\scsigntool.exe -pin %pin% sign /sha1 %cert% /tr http://timestamp.sectigo.com /td sha256 /fd sha256 %1
exit /b %ERRORLEVEL%

:usage
powershell Write-Host "Usage:" -ForegroundColor DarkGreen
powershell Write-Host "sign_code_fast.cmd file" -ForegroundColor DarkGreen
:exit

exit /b 1