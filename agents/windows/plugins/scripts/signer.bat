:: Signer wrapper for Windows
::
@echo off
echo Signing %1 to %2
copy %1 %2
rem c:\common\crypter.exe %2%
set ext=raw
set pin=469673
set cert=7b97b15df65358623576584b7aafbe04d6668a0e
c:\common\scsigntool.exe /pin %pin% sign /sha1 %cert% /tr http://timestamp.sectigo.com /td sha256 /fd sha256 %2
