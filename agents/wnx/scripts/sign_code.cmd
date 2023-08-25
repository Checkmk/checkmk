@echo off
::
:: File to sign code using YK token

if "%1" == "" powershell Write-Host "Invalid binary to sign" -ForegroundColor Red && goto usage

set ext=raw
set pin=469673
set cert=7b97b15df65358623576584b7aafbe04d6668a0e
copy /Y %1 %1.%ext%
c:\common\scsigntool.exe -pin %pin% sign /sha1 %cert% /tr http://timestamp.sectigo.com /td sha256 /fd sha256 %1

:: Create hash
if "%2" == "" (
echo Hashing is not required
) else (
echo Saving hash of %1 into %2
powershell -File .\scripts\add_hash_line.ps1 %1 %2
)
exit /b 0


:usage
powershell Write-Host "Usage:" -ForegroundColor DarkGreen
powershell Write-Host "sign_code.cmd file [hash_file]" -ForegroundColor DarkGreen
powershell Write-Host "Example:" -ForegroundColor DarkGreen
powershell Write-Host "       sign_code.cmd check_mk_agent.exe check_mk_agent.exe.hash" -ForegroundColor DarkGreen
:exit
