set VERSION="2.0.0i2"
@echo off
echo ^<^<^<win_dhcp_pools^>^>^>
netsh dhcp server show mibinfo | find /V ": dhcp." | find /v "Server may not function properly." | find /v "Unable to determine the DHCP Server version for the Server" | find /V "DHCP-Serverversion wurde" | find /V "nicht richtig funktionieren." | find /V ": dhcp server show mibinfo."
