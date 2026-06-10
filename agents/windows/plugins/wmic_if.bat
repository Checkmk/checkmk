@echo off
set CMK_VERSION="3.0.0b1"
echo ^<^<^<winperf_if_win32_networkadapter:sep^(44^)^>^>^>
wmic path Win32_NetworkAdapter get speed,macaddress,name,netconnectionid,netconnectionstatus /format:csv
