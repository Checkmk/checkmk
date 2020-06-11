rem do not use this file directly
goto exit
rem safe command to repair the WMI Perflib
lodctr /r
goto exit
cd /d %windir%\System32\Wbem

net stop winmgmt

rem winmgmt /clearadap
rem winmgmt /kill
rem winmgmt /unregserver
rem winmgmt /regserver
winmgmt /resyncperf

del %windir%\System32\Wbem\Repository /Q
del %windir%\System32\Wbem\AutoRecover /Q

for %%i in (*.dll) do Regsvr32 -s %%i
for %%i in (*.mof, *.mfl) do Mofcomp %%i
wmiadap.exe /Regsvr32
wmiapsrv.exe /Regsvr32
wmiprvse.exe /Regsvr32

net start winmgmt
:exit