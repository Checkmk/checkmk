@echo off
setlocal enableextensions enabledelayedexpansion
echo ^<^<^<lnx_if:sep^(58^)^>^>^>
set tmpfile="%temp%\check_mk-lnx_if_%random%%random%.txt"
wmic path Win32_PerfRawData_Tcpip_NetworkInterface get Name,CurrentBandwidth ^
    ,BytesReceivedPersec,PacketsReceivedPersec,PacketsReceivedErrors,PacketsReceivedDiscarded,PacketsReceivedNonUnicastPersec ^
    ,BytesSentPersec,PacketsSentPersec,PacketsOutboundErrors,PacketsOutboundDiscarded /format:csv> %tmpfile%

set ifnum=0
for /F "tokens=2-20 skip=2 delims=," %%a in ('type %tmpfile%') do (
  set /a ifnum+=1
	echo   if_!ifnum!: %%a %%j %%h %%g 0 0 0 %%i %%b %%k %%f %%e 0 0 0 0 
)
set ifnum=0
set bandwidth=0
for /F "tokens=2-20 skip=2 delims=," %%a in ('type %tmpfile%') do (
	set bandwidth=0
	set /a ifnum+=1
	echo [if_!ifnum!]
	set /a bandwidth=%%c/1000000
	if !bandwidth! GTR 0 (
		echo         Speed: !bandwidth!Mb/s
		echo         Link detected: yes
	) else (
		echo         Speed: !bandwidth!Mb/s
		echo         Link detected: no
	)
)
del %tmpfile%
endlocal

goto :end

echo debug
set ifnum=-1
for /F "tokens=2-20 delims=," %%a in ('type %tmpfile%') do (
	set /a ifnum+=1
	echo bandwidth=!bandwidth!
	echo !ifnum! %%a %%b %%c %%d %%e %%f %%g %%h %%i %%j %%k %%l %%m %%n %%o %%p %%q %%r
)


:end
endlocal


goto :eof

%%a = BytesReceivedPersec  
%%b = BytesSentPersec  
%%c = CurrentBandwidth 
%%d = Name  
%%e = PacketsOutboundDiscarded 
%%f = PacketsOutboundErrors 
%%g = PacketsReceivedDiscarded 
%%h = PacketsReceivedErrors 
%%i = PacketsReceivedNonUnicastPersec 
%%j = PacketsReceivedPersec 
%%k = PacketsSentPersec 


%%a = BytesReceivedPersec  
%%j = PacketsReceivedPersec 
%%h = PacketsReceivedErrors 
%%g = PacketsReceivedDiscarded 
0
0
0
%%i = PacketsReceivedNonUnicastPersec 

%%b = BytesSentPersec  
%%k = PacketsSentPersec 
%%f = PacketsOutboundErrors 
%%e = PacketsOutboundDiscarded 

%%c = CurrentBandwidth 
%%d = Name  
