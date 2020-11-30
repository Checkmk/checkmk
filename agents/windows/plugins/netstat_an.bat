set VERSION="2.0.0b1"
@echo off
echo ^<^<^<win_netstat^>^>^>
netstat -anp TCP & netstat -anp TCPv6 & netstat -anp UDP
