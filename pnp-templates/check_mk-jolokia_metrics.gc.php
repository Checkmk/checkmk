<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label \"GC Count\"  --title \" $servicedesc for $hostname\" ";

$def[1] =  "DEF:c=$RRDFILE[1]:$DS[1]:AVERAGE ";

$def[1] .= rrd::comment("$NAME[1]\: \\n");
$def[1] .= "AREA:c#3bfcdf:\"\" " ;
$def[1] .= "LINE1:c#00b499:\"GC Count per Minute\" " ;
$def[1] .= "GPRINT:c:LAST:\"%3.4lg LAST \" ";
$def[1] .= "GPRINT:c:AVERAGE:\"%3.4lg AVERAGE \" ";
$def[1] .= "GPRINT:c:MAX:\"%3.4lg MAX \\n\" ";

if ($WARN[1] != "") {
   $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning  at $WARN[1]$UNIT[1] \\n\" ";
}
if ($CRIT[1] != "") {
   $def[1] .= "HRULE:$CRIT[1]#FF0000:\"Critical at $CRIT[1]$UNIT[1]  \\n\" ";
}

$opt[2] = "--vertical-label \"GC Time\"  --title \" $servicedesc for $hostname\" ";

$def[2] =  "DEF:t=$RRDFILE[2]:$DS[2]:AVERAGE ";

$def[2] .= rrd::comment("$NAME[2]\: \\n");
$def[2] .= "AREA:t#ffc7ac:\"\" " ;
$def[2] .= "LINE1:t#ff6d25:\"GC Time (ms) per Minute\" " ;
$def[2] .= "GPRINT:t:LAST:\"%3.0lf$UNIT[2] LAST \" ";
$def[2] .= "GPRINT:t:AVERAGE:\"%3.2lf$UNIT[2] AVERAGE \" ";
$def[2] .= "GPRINT:t:MAX:\"%3.2lf$UNIT[2] MAX \\n\" ";
if ($WARN[2] != "") {
   $def[2] .= "HRULE:$WARN[2]#FFFF00:\"Warning  at $WARN[2]$UNIT[2] \\n\" ";
}
if ($CRIT[2] != "") {
   $def[2] .= "HRULE:$CRIT[2]#FF0000:\"Critical at $CRIT[2]$UNIT[2]  \\n\" ";
}
?>
