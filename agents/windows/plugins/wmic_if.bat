@echo off
set CMK_VERSION="2.2.0i1"
echo ^<^<^<winperf_if_win32_networkadapter:sep^(44^)^>^>^>
wmic path Win32_NetworkAdapter get speed,macaddress,name,netconnectionid,netconnectionstatus /format:csv
