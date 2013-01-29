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

$vertical = "count";
$format = "%3.0lf";
$upto = max(20, $CRIT[1]);
$color = "8040f0";
$line = "202060";

$opt[1] = " --vertical-label \"count\" -X0 -L5 -l 0 -u $upto --title \"Number of Processes\" ";

$def[1] = "DEF:count=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:count#$color:\"Processes\"     ";
$def[1] .= "LINE1:count#$line:\"\" ";
$def[1] .= "GPRINT:count:LAST:\"Current\: $format\" ";
$def[1] .= "GPRINT:count:MAX:\"Maximum\: $format \" ";
$def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning at $WARN[1]\" ";
$def[1] .= "HRULE:$CRIT[1]#FF0000:\"Critical at $CRIT[1]\" ";

if (isset($DS[2])) {
 $opt[2]  = " --vertical-label \"MB\" -l 0 --title \"Memory Usage per process\" ";
 $def[2]  = "DEF:count=$RRDFILE[1]:$DS[1]:MAX ";
 $def[2] .= "DEF:vsz=$RRDFILE[2]:$DS[2]:MAX ";
 $def[2] .= "DEF:rss=$RRDFILE[3]:$DS[3]:MAX ";
 $def[2] .= "CDEF:vszmb=vsz,1024,/,count,/ ";
 $def[2] .= "CDEF:rssmb=rss,1024,/,count,/ ";
 $def[2] .= "AREA:vszmb#90a0f0:\"Virtual size \" ";
 $def[2] .= "GPRINT:vszmb:LAST:\"Current\: %5.1lf MB\" ";
 $def[2] .= "GPRINT:vszmb:MIN:\"Min\: %5.1lf MB\" ";
 $def[2] .= "GPRINT:vszmb:MAX:\"Max\: %5.1lf MB\" ";
 $def[2] .= "AREA:rssmb#2070ff:\"Resident size\" ";
 $def[2] .= "GPRINT:rssmb:LAST:\"Current\: %5.1lf MB\" ";
 $def[2] .= "GPRINT:rssmb:MIN:\"Min\: %5.1lf MB\" ";
 $def[2] .= "GPRINT:rssmb:MAX:\"Max\: %5.1lf MB\" ";
}

if (isset($DS[3])) {
 $opt[3]  = " --vertical-label \"CPU(%)\" -l 0 -u 100 --title \"CPU Usage\" ";
 $def[3]  = "DEF:pcpu=$RRDFILE[4]:$DS[4]:MAX ";
 $def[3] .= "AREA:pcpu#30ff80:\"CPU usage (%) \" ";
 $def[3] .= "LINE:pcpu#20a060:\"\" ";
 $def[3] .= "GPRINT:pcpu:LAST:\"Current\: %4.1lf %%\" ";
 $def[3] .= "GPRINT:pcpu:MIN:\"Min\: %4.1lf %%\" ";
 $def[3] .= "GPRINT:pcpu:MAX:\"Max\: %4.1lf %%\" ";
}


?>
