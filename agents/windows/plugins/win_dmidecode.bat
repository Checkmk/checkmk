@echo off
set CMK_VERSION="2.1.0p1"

REM ***
REM * To be able to run this plugin you need to install dmidecode
REM * on your windows client.
REM *
REM * You can download dmidecode for windows from
REM * <http://gnuwin32.sourceforge.net/packages/dmidecode.htm>
REM *
REM * This plugin should work out of the box if you install dmidecode
REM * to the default location.
REM ***

echo ^<^<^<dmidecode:sep(0):nostrip^>^>^>
C:\Programme\GnuWin32\sbin\dmidecode.exe -q
