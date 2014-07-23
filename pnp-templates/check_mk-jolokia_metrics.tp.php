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


$opt[1] = "--vertical-label \"ThreadPool busy/count\"  --title \" $servicedesc for $hostname\" ";

$def[1] =  "DEF:b=$RRDFILE[1]:$DS[1]:AVERAGE ";
$def[1] .= "DEF:c=$RRDFILE[2]:$DS[2]:AVERAGE " ;


# BUSY
$def[1] .= rrd::comment("$NAME[2]\: ");
$def[1] .= "AREA:c#00ff77:\"\" " ;
$def[1] .= "LINE1:c#00b454:\"busy\" " ;
$def[1] .= "GPRINT:c:LAST:\"%3.4lg LAST \" ";
$def[1] .= "GPRINT:c:AVERAGE:\"%3.4lg AVERAGE \" ";
$def[1] .= "GPRINT:c:MAX:\"%3.4lg MAX \\n\" ";
if ($WARN[2] != "") {
   $def[1] .= "HRULE:$WARN[2]#FFFF00:\"   Warning at $WARN[2]$UNIT[2] \" ";
}
if ($CRIT[2] != "") {
   $def[1] .= "HRULE:$CRIT[2]#FF0000:\"   Critical at $CRIT[2]$UNIT[2]  \" ";
}
# MAX
$def[1] .= "HRULE:$MAX[1]#000000:\"   Max at $MAX[1] \\n\" ";


# COUNT
$def[1] .= rrd::comment("$NAME[1]\: ");
$def[1] .= "LINE1:b#00aae8:\"count\" " ;
$def[1] .= "GPRINT:b:LAST:\"%3.4lg LAST \" ";
$def[1] .= "GPRINT:b:AVERAGE:\"%3.4lg AVERAGE \" ";
$def[1] .= "GPRINT:b:MAX:\"%3.4lg MAX \\n\" ";
if ($WARN[1] != "") {
   $def[1] .= "HRULE:$WARN[1]#E5B200:\"   Warning at $WARN[1]$UNIT[1] \" ";
}
if ($CRIT[1] != "") {
   $def[1] .= "HRULE:$CRIT[1]#E50066:\"   Critical at $CRIT[1]$UNIT[1]  \\n\" ";
}

?>
