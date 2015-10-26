@echo off
echo ^<^<^<dhcp:sep^(44^)^>^>^>
wmic path Win32_NetworkAdapterConfiguration get Description, dhcpenabled /format:csv
