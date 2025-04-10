@echo off
::
:: File to sign code using YK token
::

if "%1" == "" powershell Write-Host "Invalid binary to sign" -ForegroundColor Red && goto usage


set ext=raw
set pin=469673
set cert=7b97b15df65358623576584b7aafbe04d6668a0e
copy /Y %1 %1.%ext%
c:\common\scsigntool.exe -pin %pin% sign /sha1 %cert% /tr http://timestamp.sectigo.com /td sha256 /fd sha256 %1
IF %ERRORLEVEL% EQU 0 exit /b 0
:: Retry logic... We are using powershell to sleep because in windows timeout is not available in non-interactive mode
:: 500 milliseconds is very approximately 0.5 seconds
echo RETRY...
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -nop -c "& {sleep -m 500}"    
c:\common\scsigntool.exe -pin %pin% sign /sha1 %cert% /tr http://timestamp.sectigo.com /td sha256 /fd sha256 %1
:: dont care any more
exit /b 0

:usage
powershell Write-Host "Usage:" -ForegroundColor DarkGreen
powershell Write-Host "sign_code.cmd file" -ForegroundColor DarkGreen
powershell Write-Host "Example:" -ForegroundColor DarkGreen
powershell Write-Host "       sign_code.cmd check_mk_agent.exe" -ForegroundColor DarkGreen
:exit
