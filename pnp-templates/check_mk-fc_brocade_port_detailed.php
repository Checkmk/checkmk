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

# Quellen:
#  1: txbytes
#  2: rxbytes
#  3: crcerrors
#  4: encout
#  5: c3discards

$ds_name[1] = 'Traffic';
$opt[1]  = "--vertical-label \"MB/sec\" -X0 -b 1024 --title \"Traffic for $hostname / $servicedesc\" ";
$def[1]  = "DEF:txwords=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:rxwords=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "CDEF:txbytes=txwords,4,* " ;
$def[1] .= "CDEF:rxbytes=rxwords,4,* " ;
$def[1] .= "CDEF:rxMbytes=rxbytes,1048576.0,/ " ;
$def[1] .= "CDEF:txMbytes=txbytes,1048576.0,/ " ;
$def[1] .= "CDEF:rxMbytesDraw=rxMbytes,1,* " ;
$def[1] .= "AREA:rxMbytesDraw#60a020:\"in \" " ;
$def[1] .= "GPRINT:rxMbytes:LAST:\"%.2lf MB/s last\" " ;
$def[1] .= "GPRINT:rxMbytes:AVERAGE:\"%.2lf MB/s avg\" " ;
$def[1] .= "GPRINT:rxMbytes:MAX:\"%.2lf MB/s max\\n\" " ;
$def[1] .= "CDEF:txMbytesDraw=txMbytes,-1,* " ;
$def[1] .= "AREA:txMbytesDraw#2060a0:\"out\" " ;
$def[1] .= "GPRINT:txMbytes:LAST:\"%.2lf MB/s last\" " ;
$def[1] .= "GPRINT:txMbytes:AVERAGE:\"%.2lf MB/s avg\" " ;
$def[1] .= "GPRINT:txMbytes:MAX:\"%.2lf MB/s max\\n\" " ;
if ($WARN[1] != "") {
   $def[1] .= "HRULE:$WARN[2]#ffff00:\"Warning (in)\" ";
   $def[1] .= "HRULE:-$WARN[1]#ffff00:\"Warning (out)\" ";
}
if ($CRIT[1] != "") {
   $def[1] .= "HRULE:$CRIT[2]#ff0000:\"Critical (in)\" ";
   $def[1] .= "HRULE:-$CRIT[1]#ff0000:\"Critical (out)\" ";
}
if ($MAX[1] != "")  {
   $def[1] .= "HRULE:$MAX[2]#60a020:\"Portspeed (in)\" ";
   $def[1] .= "HRULE:-$MAX[1]#2060a0:\"Portspeed (out)\" ";
# $opt[1] .= " -u $MAX[1] -l -$MAX[1]";
}

$ds_name[2] = 'Error counter';
$opt[2]  = "--vertical-label \"Error counter\" --title \"Problems on $hostname / $servicedesc\" ";
$def[2]  = "DEF:crcerrors=$RRDFILE[3]:$DS[3]:MAX " ;
$def[2] .= "DEF:encout=$RRDFILE[4]:$DS[4]:MAX " ;
$def[2] .= "DEF:c3discards=$RRDFILE[5]:$DS[5]:MAX " ;
$def[2] .= "LINE1:crcerrors#ff0000:\"CRC Errors      \" " ;
$def[2] .= "GPRINT:crcerrors:LAST:\"last\: %.0lf\\n\" " ;
$def[2] .= "LINE1:encout#60a020:\"ENC-Out         \" " ;
$def[2] .= "GPRINT:encout:LAST:\"last\: %.0lf\\n\" " ;
$def[2] .= "LINE1:c3discards#2060a0:\"Class 3 Discards\" " ;
$def[2] .= "GPRINT:c3discards:LAST:\"last\: %.0lf\\n\" " ;
?>
