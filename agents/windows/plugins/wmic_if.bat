@echo off
set CMK_VERSION="2.3.0p33"
echo ^<^<^<winperf_if_win32_networkadapter:sep^(44^)^>^>^>
wmic path Win32_NetworkAdapter get speed,macaddress,name,netconnectionid,netconnectionstatus /format:csv
