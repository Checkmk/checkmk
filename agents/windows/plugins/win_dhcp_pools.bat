@echo off
echo ^<^<^<win_dhcp_pools^>^>^>
netsh dhcp server show mibinfo | find /V ": dhcp." | find /V "DHCP-Serverversion wurde" | find /V "nicht richtig funktionieren."
