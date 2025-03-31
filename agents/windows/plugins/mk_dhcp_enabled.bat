@echo off
set CMK_VERSION="2.3.0p31"
echo ^<^<^<winperf_if_dhcp^>^>^>
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
