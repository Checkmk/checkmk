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

$opt[1] = "--vertical-label 'time (s)' -l 0  --title '$hostname: Check_MK check execution time' ";

$def[1] = "DEF:extime=$RRDFILE[1]:$DS[1]:MAX "; 
$def[1] .= "AREA:extime#d080af:\"execution time \" "; 
$def[1] .= "LINE1:extime#d020a0: "; 
$def[1] .= "GPRINT:extime:LAST:\"last\: %8.2lf s\" ";
$def[1] .= "GPRINT:extime:MAX:\"max\: %8.2lf s \" ";
$def[1] .= "GPRINT:extime:AVERAGE:\"avg\: %8.2lf s\\n\" ";

if (isset($RRDFILE[2])) {

$opt[2] = "--vertical-label 'time (s)' -l 0  --title '$hostname: Check_MK process times' ";
$def[2] = "DEF:user_time=$RRDFILE[2]:$DS[1]:MAX "; 
$def[2] .= "LINE1:user_time#d020a0:\"user time\" "; 
$def[2] .= "GPRINT:user_time:LAST:\"          last\: %8.2lf s\" "; 
$def[2] .= "GPRINT:user_time:MAX:\"max\: %8.2lf s \" ";
$def[2] .= "GPRINT:user_time:AVERAGE:\"avg\: %8.2lf s\\n\" ";

$def[2] .= "DEF:system_time=$RRDFILE[3]:$DS[1]:MAX "; 
$def[2] .= "LINE1:system_time#d08400:\"system time\" "; 
$def[2] .= "GPRINT:system_time:LAST:\"        last\: %8.2lf s\" ";
$def[2] .= "GPRINT:system_time:MAX:\"max\: %8.2lf s \" ";
$def[2] .= "GPRINT:system_time:AVERAGE:\"avg\: %8.2lf s\\n\" ";

$def[2] .= "DEF:children_user_time=$RRDFILE[4]:$DS[1]:MAX "; 
$def[2] .= "LINE1:children_user_time#308400:\"childr. user time \" "; 
$def[2] .= "GPRINT:children_user_time:LAST:\" last\: %8.2lf s\" ";
$def[2] .= "GPRINT:children_user_time:MAX:\"max\: %8.2lf s \" ";
$def[2] .= "GPRINT:children_user_time:AVERAGE:\"avg\: %8.2lf s\\n\" ";

$def[2] .= "DEF:children_system_time=$RRDFILE[5]:$DS[1]:MAX "; 
$def[2] .= "LINE1:children_system_time#303400:\"childr. system time\" "; 
$def[2] .= "GPRINT:children_system_time:LAST:\"last\: %8.2lf s\" ";
$def[2] .= "GPRINT:children_system_time:MAX:\"max\: %8.2lf s \" ";
$def[2] .= "GPRINT:children_system_time:AVERAGE:\"avg\: %8.2lf s\\n\" ";
}

?>
