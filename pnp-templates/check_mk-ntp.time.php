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

$range = $CRIT[1];

$opt[1] = "--vertical-label 'offset (ms)' -l -$range  -u $range --title '$hostname: NTP time offset to preferred peer' ";

$def[1] = "DEF:offset=$RRDFILE[1]:$DS[1]:MAX "; 
$def[1] .= "DEF:jitter=$RRDFILE[2]:$DS[2]:MAX "; 
$def[1] .= "CDEF:offsetabs=offset,ABS ";
$def[1] .= "AREA:offset#4080ff:\"time offset \" "; 
$def[1] .= "LINE1:offset#2060d0: "; 
$def[1] .= "LINE2:jitter#10c000:jitter "; 
$def[1] .= "HRULE:0#c0c0c0: ";
$def[1] .= "HRULE:$WARN[1]#ffff00:\"\" ";
$def[1] .= "HRULE:-$WARN[1]#ffff00:\"Warning\\: +/- $WARN[1] ms \" ";
$def[1] .= "HRULE:$CRIT[1]#ff0000:\"\" ";       
$def[1] .= "HRULE:-$CRIT[1]#ff0000:\"Critical\\: +/- $CRIT[1] ms \\n\" ";       
$def[1] .= "GPRINT:offset:LAST:\"current\: %.1lf ms\" ";
$def[1] .= "GPRINT:offsetabs:MAX:\"max(+/-)\: %.1lf ms \" ";
$def[1] .= "GPRINT:offsetabs:AVERAGE:\"avg(+/-)\: %.1lf ms\" ";
?>
