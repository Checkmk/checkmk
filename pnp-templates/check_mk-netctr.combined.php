<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
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
$opt[1] = "--vertical-label 'Bytes/s' -l -1024 -u 1024 --title \"$hostname / NIC $nic\" ";
# -l0 -u1048576  
#
#
$def[1] =  "DEF:rx_bytes=$RRDFILE[1]:$DS[1]:AVERAGE " ;
# $def[1] =  "DEF:rx_bytes=/var/lib/nagios/pnp/localhost/NIC_eth0.rrd:rxbytes:AVERAGE " ;
$def[1] .= "DEF:tx_bytes=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "CDEF:rx_mb=rx_bytes,1048576.0,/ " ;
$def[1] .= "CDEF:tx_mb=tx_bytes,1048576.0,/ " ;
$def[1] .= "CDEF:tx_bytes_neg=0,tx_bytes,- ";
#$def[1] .= "CDEF:rx_mb=rx_bytes,1.0,/ " ;
#$def[1] .= "CDEF:tx_mb=tx_bytes,1.0,/ " ;
$def[1] .= "DEF:rx_errors=$RRDFILE[5]:$DS[5]:MAX " ;
$def[1] .= "DEF:tx_errors=$RRDFILE[6]:$DS[6]:MAX " ;
$def[1] .= "DEF:tx_collisions=$RRDFILE[7]:$DS[7]:MAX " ;
$def[1] .= "CDEF:errors=rx_errors,tx_errors,+ ";
$def[1] .= "CDEF:problems_x=errors,tx_collisions,+ ";
$def[1] .= "CDEF:problems=problems_x,1000000,* "; # Skaliere Probleme hoch, damit man was sieht

$def[1] .= "AREA:problems#ff0000:\"Errors \" " ;
$def[1] .= "GPRINT:problems:LAST:\"%.0lf/s\" " ;
$def[1] .= "AREA:rx_bytes#20a020:\"Receive \" " ;
$def[1] .= "GPRINT:rx_mb:LAST:\"%.2lfMB/s\" " ;
$def[1] .= "AREA:tx_bytes_neg#0060a0:\"Transmit \" " ;
$def[1] .= "HRULE:0#c0c0c0 ";
$def[1] .= "GPRINT:tx_mb:LAST:\"%.2lfMB/s\" " ;

?>
