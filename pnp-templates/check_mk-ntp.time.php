<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$range = $CRIT[1];

$opt[1] = "--vertical-label 'offset (ms)' -X 0 -l -$range  -u $range --title '$hostname: NTP time offset to preferred peer' ";

$def[1] = "DEF:offset=$RRDFILE[1]:$DS[1]:MAX ";
if (isset($DS[2])) # missing for chrony
    $def[1] .= "DEF:jitter=$RRDFILE[2]:$DS[2]:MAX ";
$def[1] .= "CDEF:offsetabs=offset,ABS ";
$def[1] .= "AREA:offset#4080ff:\"time offset \" ";
$def[1] .= "LINE1:offset#2060d0: ";
if (isset($DS[2])) # missing for chrony
    $def[1] .= "LINE2:jitter#10c000:jitter ";
$def[1] .= "HRULE:0#c0c0c0: ";
$def[1] .= "HRULE:$WARN[1]#ffff00:\"\" ";
$def[1] .= "HRULE:-$WARN[1]#ffff00:\"Warning\\: +/- $WARN[1] ms \" ";
$def[1] .= "HRULE:$CRIT[1]#ff0000:\"\" ";
$def[1] .= "HRULE:-$CRIT[1]#ff0000:\"Critical\\: +/- $CRIT[1] ms \\n\" ";
$def[1] .= "GPRINT:offset:LAST:\"current\: %.4lf ms\" ";
$def[1] .= "GPRINT:offsetabs:MAX:\"max(+/-)\: %.4lf ms \" ";
$def[1] .= "GPRINT:offsetabs:AVERAGE:\"avg(+/-)\: %.4lf ms\" ";
?>
