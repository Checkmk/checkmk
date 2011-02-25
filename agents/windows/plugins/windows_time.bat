@echo off

REM Windows time checks
REM <fh@mathias-kettner.de>
REM 
REM 

REM Win2008 
set W2K8 = "Microsoft Windows [Version 6.0.6002]"


echo "<<<windows_time>>>"

REM only w2k8 / vista /win7 are able to report ntp status.
if ver = "%W2K8%" w32tm /query /status

REM win2003 can _test_ the ntp server using w32tm /once, but we don't want
REM to test EVERY minute, it takes a few seconds and will hammer the NTP server.
REM I very much recommend to monitor for w32time errors in eventlog instead.

REM all others since W2K can at least report their primary SNTP or NTP server
REM the MS-supplied timeserver is usually blocked in corporate networks, but 
REM windows will default to it.
net time /querysntp    

