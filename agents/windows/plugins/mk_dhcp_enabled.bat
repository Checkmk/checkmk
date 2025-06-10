@echo off
set CMK_VERSION="2.3.0p35"
echo ^<^<^<winperf_if_dhcp^>^>^>
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
