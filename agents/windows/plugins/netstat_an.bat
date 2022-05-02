@echo off
set CMK_VERSION="2.1.0b8"
echo ^<^<^<win_netstat^>^>^>
netstat -anp TCP & netstat -anp TCPv6 & netstat -anp UDP
