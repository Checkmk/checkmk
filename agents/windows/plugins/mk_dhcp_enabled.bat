@echo off
echo ^<^<^<dhcp^>^>^>
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled
