@echo off
set CMK_VERSION="2.3.0b1"
echo ^<^<^<win_netstat^>^>^>
netstat -anp TCP & netstat -anp TCPv6 & netstat -anp UDP
