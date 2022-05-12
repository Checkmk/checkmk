@echo off
set CMK_VERSION="2.1.0b9"
echo ^<^<^<winperf_if_dhcp^>^>^>
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
