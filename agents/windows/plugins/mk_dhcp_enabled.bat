set VERSION="2.0.0i2"
@echo off
echo ^<^<^<winperf_if^>^>^>
echo [dhcp_start]
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
echo [dhcp_end]
