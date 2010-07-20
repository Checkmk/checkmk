@echo off

REM This can be used as local check for the windows Check_MK agent.
REM The check tries to query the host "192.168.123.2" and forward lookup the
REM domain "domain.de" and expects whe addresses "192.168.123.1" and
REM "192.168.123.2" as answer.
REM
REM When more or less addresses are found the check becomes critical.
REM
REM To be able to use this check you need to put this script in your
REM check_mk_agent\local directory and the file nslookup.vbs in the
REM check_mk_agent\lib directory.

cscript //NoLogo lib/nslookup.vbs nslookup_domain.de 192.168.123.2 domain.de forward 192.168.123.1 192.168.123.2
