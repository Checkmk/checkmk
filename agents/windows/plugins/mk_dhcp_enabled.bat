@echo off
set CMK_VERSION="2.6.0b1"
echo ^<^<^<winperf_if_dhcp^>^>^>
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
