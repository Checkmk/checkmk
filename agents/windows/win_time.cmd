# DO NOT USE YET!

@echo off

REM ***
REM Query Windows Time daemons
REM Only Windows 2008 can give a useful status of the current win32time status.
REM ***

echo ^<^<^<win_time^>^>^>
REM read in windows version
ver

REM by standard, just query the timeserver.
net time /querysntp | findstr SNTP

REM if we're on W2K8 it is possible to query the timeserver status
REM otherwise this will fail.
w32tm /query /status
