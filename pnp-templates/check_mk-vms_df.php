<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$fsname = str_replace("_", "/", substr($servicedesc, 3));
$sizegb = sprintf("%.1f", $MAX[1] / 1024.0);
$maxgb = $MAX[1] / 1024.0;
$warngb = $WARN[1] / 1024.0;
$critgb = $CRIT[1] / 1024.0;
$warngbtxt = sprintf("%.1f", $warngb);
$critgbtxt = sprintf("%.1f", $critgb);

# disk utilization
$opt[1] = "--vertical-label GB -l 0 -u $maxgb --title \"$hostname: Filesystem $fsname ($sizegb GB)\" ";

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

# IO operation per second
$opt[2] = "--vertical-label 'IO ops/sec' --title \"$hostname: IO operations / sec\" ";

$def[2] = "DEF:iops=$RRDFILE[2]:$DS[2]:MAX " ;
$def[2] .= "LINE1:iops#00ff00: ";


?>
