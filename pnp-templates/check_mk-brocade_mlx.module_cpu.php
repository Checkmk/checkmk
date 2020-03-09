<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label '%' -l0  -u 100 --title \"CPU Utilization\" ";
#
$def[1]  =  "DEF:util1=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .=  "DEF:util5=$RRDFILE[2]:$DS[1]:AVERAGE " ;
$def[1] .=  "DEF:util60=$RRDFILE[3]:$DS[1]:AVERAGE " ;
$def[1] .=  "DEF:util300=$RRDFILE[4]:$DS[1]:AVERAGE " ;

$def[1] .= "AREA:util60#60f020:\"Utilization 60s\" " ;
$def[1] .= "GPRINT:util60:MIN:\"Min\: %2.1lf%%\" " ;
$def[1] .= "GPRINT:util60:MAX:\"Max\: %2.1lf%%\" " ;
$def[1] .= "GPRINT:util60:LAST:\"Last\: %2.1lf%%\" " ;
$def[1] .= "HRULE:$WARN[3]#FFFF00:\"Warn\" " ;
$def[1] .= "HRULE:$CRIT[3]#FF0000:\"Crit\\n\" " ;

$def[1] .= "LINE:util1#000000:\"Util 1s \" " ;
$def[1] .= "GPRINT:util1:LAST:\"Last\: %2.1lf%%\" " ;

$def[1] .= "LINE:util5#0000ff:\"5s \" " ;
$def[1] .= "GPRINT:util5:LAST:\"Last\: %2.1lf%%\" " ;

$def[1] .= "LINE:util300#ff00ff:\"300s \" " ;
$def[1] .= "GPRINT:util300:LAST:\"Last\: %2.1lf%%\\n\" " ;
?>
