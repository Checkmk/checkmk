set VERSION="2.0.0b4"
@echo off
echo ^<^<^<winperf_if:sep^(44^)^>^>^>
wmic path Win32_NetworkAdapter get speed,macaddress,name,netconnectionid,netconnectionstatus /format:csv
