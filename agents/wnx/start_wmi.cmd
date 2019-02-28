@echo off
rem Start Wmi Adapter
rem WE NEED THIS FOR RELIABLE TESTING

rem AT > NUL
net session > nul
IF %ERRORLEVEL% EQU 0 (
    ECHO starting wmi...
) ELSE (
    ECHO you are NOT Administrator. YOU CANNOT DO IT!
    EXIT /B 1
)

sc config wmiApSrv start=auto
net start wmiApSrv
