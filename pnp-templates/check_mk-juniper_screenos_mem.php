<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

if ($MAX[1]/1024/1024 > 10000) {
    $scale = 1024 * 1024 * 1024;
    $unit = 'GB';
}
else {
    $scale = 1024 * 1024;
    $unit = 'MB';
}

$total = sprintf("%.2f", $MAX[1] / $scale);
$warn = sprintf("%.2f", $WARN[1] / $scale);
$crit = sprintf("%.2f", $CRIT[1] / $scale);

$opt[1] = "--vertical-label $unit -l 0 --title \"Main Memory (RAM)\" -X0 --upper-limit " . $total;
#

$def[1]  = "DEF:used_bytes=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "CDEF:used=used_bytes,$scale,/ ";
$def[1] .= "AREA:used#60f020:\"Used\" " ;
$def[1] .= "GPRINT:used:MIN:\"Min\: %2.1lf $unit\" " ;
$def[1] .= "GPRINT:used:MAX:\"Max\: %2.1lf $unit\" " ;
$def[1] .= "GPRINT:used:LAST:\"Last\: %2.1lf $unit\\n\" " ;
$def[1] .= "HRULE:$warn#FFFF00:\"Warn\" ";
$def[1] .= "HRULE:$crit#FF0000:\"Crit\" ";
$def[1] .= "HRULE:$total#000000:\"RAM installed $total $unit\\n\" ";
?>
