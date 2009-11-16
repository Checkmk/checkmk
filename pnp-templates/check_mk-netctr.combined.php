<?php
# +------------------------------------------------------------------+
# |                     _           _           _                    |
# |                  __| |_  ___ __| |__  _ __ | |__                 |
# |                 / _| ' \/ -_) _| / / | '  \| / /                 |
# |                 \__|_||_\___\__|_\_\_|_|_|_|_\_\                 |
# |                                   |___|                          |
# |              _   _   __  _         _        _ ____               |
# |             / | / | /  \| |__  ___| |_ __ _/ |__  |              |
# |             | |_| || () | '_ \/ -_)  _/ _` | | / /               |
# |             |_(_)_(_)__/|_.__/\___|\__\__,_|_|/_/                |
# |                                            check_mk 1.1.0beta17  |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
# 
# This file is part of check_mk 1.1.0beta17.
# The official homepage is at http://mathias-kettner.de/check_mk.
# 
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

#
# Datensatze:
#    1: rx_bytes
#    2: tx_bytes
#    3: rx_packets
#    4: tx_packets
#    5: rx_errors
#    6: tx_errors
#    7: tx_collisions
                        

#
$x = explode("_", $servicedesc);
$nic = $x[1];
$opt[1] = "--vertical-label 'Byte/s' -l0 -u1048576  --title \"$hostname / NIC $nic\" ";
#
#
#
$def[1] =  "DEF:rx_bytes=$rrdfile:$DS[1]:MAX " ;
$def[1] .= "DEF:tx_bytes=$rrdfile:$DS[2]:MAX " ;
#$def[1] .= "CDEF:rx_mb=rx_bytes,1048576.0,/ " ;
#$def[1] .= "CDEF:tx_mb=tx_bytes,1048576.0,/ " ;
$def[1] .= "CDEF:rx_mb=rx_bytes,1.0,/ " ;
$def[1] .= "CDEF:tx_mb=tx_bytes,1.0,/ " ;
$def[1] .= "DEF:rx_errors=$rrdfile:$DS[5]:MAX " ;
$def[1] .= "DEF:tx_errors=$rrdfile:$DS[6]:MAX " ;
$def[1] .= "DEF:tx_collisions=$rrdfile:$DS[7]:MAX " ;
$def[1] .= "CDEF:errors=rx_errors,tx_errors,+ ";
$def[1] .= "CDEF:problems_x=errors,tx_collisions,+ ";
$def[1] .= "CDEF:problems=problems_x,1000000,* "; # Skaliere Probleme hoch, damit man was sieht

$def[1] .= "AREA:problems#ff0000:\"Errors \" " ;
$def[1] .= "GPRINT:problems:LAST:\"%.0lf/s\" " ;
$def[1] .= "LINE:rx_mb#2060a0:\"Receive \" " ;
$def[1] .= "GPRINT:rx_mb:LAST:\"%.1lfMB/s\" " ;
$def[1] .= "LINE:tx_mb#60a020:\"Transmit \" " ;
$def[1] .= "GPRINT:tx_mb:LAST:\"%.1lfMB/s\" " ;

?>
