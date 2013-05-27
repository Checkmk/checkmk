@echo off

REM ***
REM * To be able to run this check you need apprpriate credentials
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

echo ^<^<^<ad_replication^>^>^>
dsquery server | find /I "CN=%COMPUTERNAME%," > nul
if ERRORLEVEL 0 repadmin /showrepl /csv
