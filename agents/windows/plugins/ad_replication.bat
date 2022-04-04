@echo off
set CMK_VERSION="2.1.0b5"

REM ***
REM * Following information concerns only Windows Server <2012R2
REM *
REM * To be able to run this check you need appropriate credentials
REM * in the target domain.
REM *
REM * Normally the Check_MK agent runs as sevice with local system
REM * credentials which are not enough for this check.
REM *
REM * To solve this problem you can do e.g. the following:
REM *
REM * - Change the account the service is being started with to a
REM *   domain user account with enough permissions on the DC.
REM *
REM ***
REM * If tools to manage  DC are absent,
REM   then plugin outputs nothing
REM * If tools to manage  DC are present but the computer is not DC,
REM   then plugin outputs only header
REM * If the computer is DC,
REM   then plugin works as usually
REM ***
REM * repadmin reports 'repadmin_ERROR' when the tools to manage DC
REM * have been installed on Windows Desktop OS(10, 8, 7 and so on)
REM * We are using 'find /V' to skip such line from the output
REM ***

where /Q repadmin > nul
if ERRORLEVEL 1 goto SERVER_NOT_IN_DC_LIST
echo ^<^<^<ad_replication^>^>^>
repadmin /showrepl /csv	| find /V "repadmin_ERROR,"
:SERVER_NOT_IN_DC_LIST
