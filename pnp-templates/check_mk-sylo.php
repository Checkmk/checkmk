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


$ds_name[1] = 'Space';
$opt[1]  = "--vertical-label \"Used space (MB)\" -l0 -X0 -u $MAX[3] -b 1024 --title \"Used space in syslog spooler for $hostname\" ";
$def[1]  = "DEF:used=$RRDFILE[3]:$DS[3]:MAX " ;
$def[1] .= "AREA:used#ff8800:\"Used space \" ";
$def[1] .= "HRULE:$WARN[3]#FFFF00:\"Warning at $WARN[3] MB\" ";
$def[1] .= "HRULE:$CRIT[3]#FF0000:\"Critical at $CRIT[3] MB\" ";
$def[1] .= "HRULE:$MAX[3]#0044ff:\"Spool size $MAX[3] MB\" ";
$def[1] .= "GPRINT:used:LAST:\"%.1lf MB last\" " ;
$def[1] .= "GPRINT:used:AVERAGE:\"%.1lf MB avg\" " ;
$def[1] .= "GPRINT:used:MAX:\"%.1lf MB max\\n\" " ;

$ds_name[2] = 'Traffic';
$opt[2]  = "--vertical-label \"Bytes/sec\" -X0 -b 1024 --title \"Syslog traffic for $hostname\" ";
$def[2]  = "DEF:inbytes=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[2] .= "DEF:outbytes=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[2] .= "CDEF:outbytesn=0,outbytes,- " ;
$def[2] .= "AREA:inbytes#ff8800:\"Ingoing \" ";
$def[2] .= "GPRINT:inbytes:LAST:\"%.0lf B/s last\" " ;
$def[2] .= "GPRINT:inbytes:AVERAGE:\"%.0lf MB/s avg\" " ;
$def[2] .= "GPRINT:inbytes:MAX:\"%.0lf B/s max\\n\" " ;
$def[2] .= "AREA:outbytesn#44ccff:\"Outgoing\" ";
$def[2] .= "GPRINT:outbytes:LAST:\"%.0lf B/s last\" " ;
$def[2] .= "GPRINT:outbytes:AVERAGE:\"%.0lf MB/s avg\" " ;
$def[2] .= "GPRINT:outbytes:MAX:\"%.0lf B/s max\\n\" " ;

?>
