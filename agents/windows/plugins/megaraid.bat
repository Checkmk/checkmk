@ECHO off & setlocal EnableDelayedExpansion
set CMK_VERSION="2.0.0p23"
REM **********************************************************************
REM * Script: megaraid.bat
REM * Author: Josef Hack
REM * Mail: josef.hack@rvs.at
REM * Version: 1.0
REM * Date: 2.4.2012
REM * Details: get the status of megaraid adapters
REM *
REM * To be able to run this check you need to install MegaCli.exe on your windows client.
REM *
REM * You can download MegaCli.exe for windows from
REM * http://www.lsi.com/
REM *
REM * after install MegaCli.exe modify the Path in the MegaCli Variable
REM *
REM **********************************************************************

REM customize Megcli and TEMP Path to your needs
SET "MegaCli=C:\Program Files\LSI Corporation\MegaCLI\MegaCli.exe"
SET "TEMP=C:\temp"

SET "enclist=!TEMP!\enclist.txt"
SET "pdlist=!TEMP!\pdlist.txt"
SET "tmpfile=!TEMP!\tmp.txt"

REM check Megacli and temp path
IF NOT EXIST !MegaCli! GOTO END
IF NOT EXIST !TEMP!\NUL MD !TEMP!

REM create searchlist
ECHO Enclosure> "!enclist!"
ECHO Device ID>> "!enclist!"
ECHO Enclosure> "!pdlist!"
ECHO Raw Size>> "!pdlist!"
ECHO Slot Number>> "!pdlist!"
ECHO Device Id>> "!pdlist!"
ECHO Firmware state>> "!pdlist!"
ECHO Inquiry>> "!pdlist!"

REM get physical disc info
ECHO ^<^<^<megaraid_pdisks^>^>^>
"!MegaCli!"  -EncInfo -aALL -NoLog | FINDSTR /g:!enclist! > !tmpfile!
FOR /F "tokens=1,2,3,4,5,6* delims=:+ " %%h in (!tmpfile!) do (

	IF "%%h" == "Enclosure"  (
		ECHO %%i|FINDSTR /r "[^0-9]" > NUL
		IF ERRORLEVEL 1 (
			SET part_a=%%h %%i
		)
	)
	IF "%%h" == "Device"  (
		ECHO dev2enc !part_a! %%h %%i %%j
		SET part_a=
	)
 )
"!MegaCli!" -PDList -aALL -NoLog  | FINDSTR /g:!pdlist!

REM get logical disc info
ECHO ^<^<^<megaraid_ldisks^>^>^>
"!MegaCli!" -LDInfo -Lall -aALL -NoLog | FINDSTR "Size State Number Adapter Virtual"

REM get bbu info
ECHO ^<^<^<megaraid_bbu^>^>^>
"!MegaCli!" -AdpBbuCmd -GetBbuStatus -aAll -NoLog | FINDSTR /V "Exit"

REM delete tmpfiles
DEL "!tmpfile!"
DEL "!enclist!"
DEL "!pdlist!"

:END
