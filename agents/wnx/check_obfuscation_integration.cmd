@echo off
rem 
rem This files check integration of the python obfuscating module with windows agent de obfuscating
rem Script requires that some file to be present
rem ALso NOW script requires the presence of the 27.32 python
rem

rem DEFINES:
set python=c:\python27.32\python.exe
set script=..\..\cmk\utils\obfuscation.py
set agent=..\..\artefacts\check_mk_service32.exe
set script=..\..\cmk\utils\obfuscation.py
set file_1=c:\dev\shared\cmk-update-agent.exe
set file_2=c:\dev\shared\test_file.txt

rem Check that all mandatory files exist
if not exist %python% powershell Write-Host "[-]You have to have install python in folder %python%" -foreground Red && exit /b 2 
powershell Write-Host "[+] python is `'%python%`'" -foreground Green
if not exist %script% powershell Write-Host "[-] You have to have script %script%" -foreground Red && exit /b 3 
powershell Write-Host "[+] script is `'%script%`'" -foreground Green
if not exist %file_1% powershell Write-Host "[-] You have to have file %file_1%" -foreground Red && exit /b 4 
powershell Write-Host "[+] file 1 is `'%file_1%`'" -foreground Green
if not exist %file_2% powershell Write-Host "[-] You have to have script %file_2%" -foreground Red && exit /b 5 
powershell Write-Host "[+] file 2 is `'%file_2%`'" -foreground Green
if not exist %agent% powershell Write-Host "[-] You have to have %agent%" -foreground Red && exit /b 5 
powershell Write-Host "[+] agent is `'%agent%`'" -foreground Green


rem Clean output
powershell Write-Host "    cleaning..." -foreground cyan
if exist %file_1%.enc del %file_1%.enc > nul
if exist %file_2%.enc del %file_2%.enc > nul
if exist %file_1%.dec del %file_1%.dec > nul
if exist %file_2%.dec del %file_2%.dec > nul
if exist %file_1%.dec.agent del %file_1%.dec.agent > nul
if exist %file_2%.dec.agent del %file_2%.dec.agent > nul
if exist %file_1%.enc powershell Write-Host "[-] Can`'t delete %file_1%" -foreground Red && exit /b 6 
if exist %file_2%.enc powershell Write-Host "[-] Can`'t delete %file_2%" -foreground Red && exit /b 7 

rem Python internal Integration
powershell Write-Host "....Python internal integration..." -foreground cyan
powershell Write-Host "....encrypting is `'%file_1%`'..." -foreground Cyan
%python% %script% encrypt %file_1% %file_1%.enc
powershell Write-Host "....encrypting is `'%file_2%`'..." -foreground Cyan
%python% %script% encrypt %file_2% %file_2%.enc
if not exist %file_1%.enc powershell Write-Host "[-] Can`'t create %file_1%.enc" -foreground Red && exit /b 8 
if not exist %file_2%.enc powershell Write-Host "[-] Can`'t create %file_2%.enc" -foreground Red && exit /b 9 
powershell Write-Host "....decrypting is `'%file_1%`'..." -foreground Cyan
%python% %script% decrypt %file_1%.enc %file_1%.dec
powershell Write-Host "....decrypting is `'%file_2%`'..." -foreground Cyan
%python% %script% decrypt %file_2%.enc %file_2%.dec
if not exist %file_1%.dec powershell Write-Host "[-] Can`'t create %file_1%.dec" -foreground Red && exit /b 10 
if not exist %file_2%.dec powershell Write-Host "[-] Can`'t create %file_2%.dec" -foreground Red && exit /b 11

fc /b %file_1% %file_1%.dec > nul
if not %errorlevel% == 0 powershell Write-Host "[-] decryption is failed by python `'%file_1%`'" -foreground Red && exit /b 12
powershell Write-Host "[+] correct `'%file_1%`'" -foreground Green
fc /b %file_2% %file_2%.dec > nul
if not %errorlevel% == 0 powershell Write-Host "[-] decryption is failed by python `'%file_2%`'" -foreground Red && exit /b 13
powershell Write-Host "[+] correct `'%file_2%`'" -foreground Green
%agent% hc_decrypt_python %file_1%.enc %file_1%.dec.agent
if not %errorlevel% == 0 powershell Write-Host "[-] decryption is failed `'%file_1%.enc`'" -foreground Red && exit /b 12
powershell Write-Host "[+] correct `'%file_1%.enc`'" -foreground Green

rem Agent-Python integration
powershell Write-Host "....Agent - Python integration..." -foreground cyan
%agent% hc_decrypt_python %file_2%.enc %file_2%.dec.agent
if not %errorlevel% == 0 powershell Write-Host "[-] decryption is failed `'%file_2%.enc`'" -foreground Red && exit /b 12
powershell Write-Host "[+] correct `'%file_2%.enc`'" -foreground Green


fc /b %file_1% %file_1%.dec.agent > nul
if not %errorlevel% == 0 powershell Write-Host "[-] decryption is failed by agent `'%file_1%`'" -foreground Red && exit /b 12
powershell Write-Host "[+] correct `'%file_1%`'" -foreground Green

fc /b %file_2% %file_2%.dec.agent > nul
if not %errorlevel% == 0 powershell Write-Host "[-] decryption is failed by agent `'%file_2%`'" -foreground Red && exit /b 13
powershell Write-Host "[+] correct `'%file_2%`'" -foreground Green


powershell Write-Host "[+] finished`r" -foreground Green
