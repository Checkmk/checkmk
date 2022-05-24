@echo off
set CMK_VERSION="2.0.0p26"
echo ^<^<^<winperf_if^>^>^>
echo [dhcp_start]
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
echo [dhcp_end]
