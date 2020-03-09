<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'MEMORY(MB)' --upper-limit " . ($MAX[1] * 120 / 100) . " -l0  --title \"Memory usage $hostname\" ";

$maxgb = sprintf("%.1f", $MAX[1] / 1024.0);

$def[1] =  "DEF:ram=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:swap=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "DEF:virt=$RRDFILE[3]:$DS[3]:AVERAGE " ;
$def[1] .= "HRULE:$MAX[3]#000080:\"RAM+SWAP installed\" ";
$def[1] .= "HRULE:$MAX[1]#2040d0:\"$maxgb GB RAM installed\" ";
$def[1] .= "HRULE:$WARN[3]#FFFF00:\"Warning\" ";
$def[1] .= "HRULE:$CRIT[3]#FF0000:\"Critical\\n\" ";

$def[1] .= "'COMMENT:\\n' " ;
$def[1] .= "AREA:ram#80ff40:\"RAM used     \" " ;
$def[1] .= "GPRINT:ram:LAST:\"%6.0lf MB last\" " ;
$def[1] .= "GPRINT:ram:AVERAGE:\"%6.0lf MB avg\" " ;
$def[1] .= "GPRINT:ram:MAX:\"%6.0lf MB max\\n\" ";

$def[1] .= "AREA:swap#008030:\"SWAP used    \":STACK " ;
$def[1] .= "GPRINT:swap:LAST:\"%6.0lf MB last\" " ;
$def[1] .= "GPRINT:swap:AVERAGE:\"%6.0lf MB avg\" " ;
$def[1] .= "GPRINT:swap:MAX:\"%6.0lf MB max\\n\" " ;

$def[1] .= "LINE:virt#000000:\"RAM+SWAP used\" " ;
$def[1] .= "GPRINT:virt:LAST:\"%6.0lf MB last\" " ;
$def[1] .= "GPRINT:virt:AVERAGE:\"%6.0lf MB avg\" " ;
$def[1] .= "GPRINT:virt:MAX:\"%6.0lf MB max\\n\" " ;
?>
