@echo off

REM This can be used as local check for the windows Check_MK agent.
REM The check tries to query the host "192.168.123.2" and reverse lookup the
REM address "192.168.123.1" and expects the answer "dc.domain.de".
REM
REM When more or less names are found the check becomes critical.
REM
REM To be able to use this check you need to put this script in your
REM check_mk_agent\local directory and the file nslookup.vbs in the
REM check_mk_agent\lib directory.

cscript //NoLogo lib/nslookup.vbs nslookup_reverse 192.168.123.2 192.168.123.1 forward dc.domain.de
