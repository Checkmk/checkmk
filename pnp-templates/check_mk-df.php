<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

setlocale(LC_ALL, "POSIX");

# RRDtool Options
#$servicedes=$NAGIOS_SERVICEDESC

$fsname = str_replace("_", "/", substr($servicedesc, 3));
$fstitle = $fsname;

# Hack for windows: replace C// with C:\
if (strlen($fsname) == 3 && substr($fsname, 1, 2) == '//') {
    $fsname = $fsname[0] . "\:\\\\";
    $fstitle = $fsname[0] . ":\\";
}

$sizegb = sprintf("%.1f", $MAX[1] / 1024.0);
$maxgb = $MAX[1] / 1024.0;
$warngb = $WARN[1] / 1024.0;
$critgb = $CRIT[1] / 1024.0;
$warngbtxt = sprintf("%.1f", $warngb);
$critgbtxt = sprintf("%.1f", $critgb);

$opt[1] = "--vertical-label GB -l 0 -u $maxgb --title '$hostname: Filesystem $fstitle ($sizegb GB)' ";

# First graph show current filesystem usage
$def[1] = "DEF:mb=$RRDFILE[1]:$DS[1]:MAX "; 
$def[1] .= "CDEF:var1=mb,1024,/ ";
$def[1] .= "AREA:var1#00ffc6:\"used space on $fsname\\n\" "; 
$def[1] .= "LINE1:var1#226600: "; 
$def[1] .= "HRULE:$maxgb#003300:\"Size ($sizegb GB) \" ";
$def[1] .= "HRULE:$warngb#ffff00:\"Warning at $warngbtxt GB \" ";
$def[1] .= "HRULE:$critgb#ff0000:\"Critical at $critgbtxt GB \\n\" ";
$def[1] .= "GPRINT:var1:LAST:\"current\: %6.2lf GB\" ";
$def[1] .= "GPRINT:var1:MAX:\"max\: %6.2lf GB \" ";
$def[1] .= "GPRINT:var1:AVERAGE:\"avg\: %6.2lf GB\" ";

# Second graph is optional and shows trend
if (isset($DS[2])) {
    $size_mb_per_hours = floatval($MAX[3]); // this is size_mb / range(hours)
    $size_mb = floatval($MAX[1]);
    $hours = 1.0 / ($size_mb_per_hours / $size_mb);
    $range = sprintf("%.1fh", $hours);

    $opt[2] = "--vertical-label '+/- MB / $range' -l -1 -u 1 --title '$hostname: Trend for $fstitle' ";
    $def[2] = "DEF:growth=$RRDFILE[2]:$DS[2]:AVERAGE ";
    $def[2] .= "DEF:trend=$RRDFILE[3]:$DS[3]:AVERAGE ";
    $def[2] .= "CDEF:growth_pos=growth,0,MAX ";
    $def[2] .= "CDEF:growth_neg=growth,0,MIN ";
    $def[2] .= "HRULE:0#c0c0c0 ";
    $def[2] .= "AREA:growth_pos#3060f0:\"Grow\" "; 
    $def[2] .= "AREA:growth_neg#30f060:\"Shrink \" "; 
    $def[2] .= "LINE1:trend#000000:\"Trend  \" "; 
    if ($WARN[3])
        $def[2] .= "LINE1:$WARN[3]#ffff00:\"Warning at $WARN[3]MB/$range\" ";
    if ($CRIT[3])
        $def[2] .= "LINE1:$CRIT[3]#ff0000:\"Critical at $CRIT[3]MB/$range\" ";
    $def[2] .= "COMMENT:\"\\n\" ";
    $def[2] .= "GPRINT:growth:LAST:\"Current\: %+9.2lf MB/$range\" ";
    $def[2] .= "GPRINT:trend:LAST:\"  Trend\: %+7.2lf MB/$range\\n\" "; 
}


?>
