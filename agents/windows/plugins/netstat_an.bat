@echo off
set CMK_VERSION="2.6.0b1"
echo ^<^<^<win_netstat^>^>^>
netstat -anp TCP & netstat -anp TCPv6 & netstat -anp UDP
