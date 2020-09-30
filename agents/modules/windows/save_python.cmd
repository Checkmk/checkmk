@rem  Python installer script
@rem  May be called only from exec_cmd.bat

@setlocal enableextensions enabledelayedexpansion
@echo off

@rem echo on
if not defined pexe powershell Write-Host "Must be called from the exec_cmd.bat, pexe" -foreground Red && exit /b 3
if not defined pexe_uninstall powershell Write-Host "Must be called from the exec_cmd.bat, pexe_uninstall" -foreground Red && exit /b 3
if not defined install_dir powershell Write-Host "Must be called from the exec_cmd.bat, install_dir" -foreground Red && exit /b 3
if not defined uninstall_dir powershell Write-Host "Must be called from the exec_cmd.bat, uninstall_dir" -foreground Red && exit /b 3
if not defined save_dir powershell Write-Host "Must be called from the exec_cmd.bat, save_dir" -foreground Red && exit /b 3
if not exist %pexe% powershell Write-Host "%pexe% doesnt exist" -foreground Red && exit /b 3
powershell Write-Host "Saving Python ..." -foreground Cyan 
set str1=%save_dir%
if not x%str1:tmp=%==x%str1% powershell Write-Host "Looks as good path" -Foreground Green && goto processing
powershell Write-Host "save_dir should point on valid path with tmp inside" -foreground Red 
exit /b 4
:processing
mkdir %save_dir% 2> nul
set last_dir=%cd%
cd %save_dir% || Powershell Write-Host "`'%save_dir%`' absent" -Foreground red && exit /b 5
if x%str1:to_save=%==x%str1% powershell Write-Host "`'%save_dir%`' Looks as bad path" -Foreground red && exit /b 6
if not %cd%== %save_dir% powershell Write-Host "`'%save_dir%`' can enter dir" -Foreground red && exit /b 7
del * /S /Q >nul
cd %last_dir%
xcopy %install_dir% %save_dir% /E >nul || powershell Write-Host "`'%save_dir%`' xcopy failed" -Foreground red && exit /b 8

