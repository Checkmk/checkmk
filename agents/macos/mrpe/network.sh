#!/bin/bash

interfaces=$(networksetup -listallhardwareports | grep Device | awk '{print $2}')
interfaces+=" $(ifconfig | grep -E '^utun*' | sed 's/\(^utun[^:]*\):.*/\1/g')"

for interface in $interfaces; do
  inet=$(ifconfig $interface | grep 'inet ' | awk '{print $2}')

  if [ -n "$inet" ]; then
    ether=$(ifconfig $interface | grep 'ether ' | awk '{print $2}')
    if [ -n "$ether" ]; then
      echo -n "[$interface]: $inet (MAC: $ether)   " 
    else
      echo -n "[$interface]: $inet (VPN)"
    fi
  fi
done
echo
exit 0
