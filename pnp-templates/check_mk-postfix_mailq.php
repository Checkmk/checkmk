<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# (length=22;10;20;; size=2048;;;;)
$opt[1] = "--vertical-label Mails -l0  --title \"Mail Queue Length\" ";
$def[1] =  "DEF:length=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "HRULE:$WARN[1]#FFFF00 ";
$def[1] .= "HRULE:$CRIT[1]#FF0000 ";
$def[1] .= "AREA:length#6890a0:\"Mails\" " ;
$def[1] .= "LINE:length#2060a0 " ;
$def[1] .= "GPRINT:length:LAST:\"%6.2lf last\" " ;
$def[1] .= "GPRINT:length:AVERAGE:\"%6.2lf avg\" " ;
$def[1] .= "GPRINT:length:MAX:\"%6.2lf max\\n\" ";


$opt[2] = "--vertical-label MBytes -b1024 -X6 -l0 --title \"Mail Queue Size\" ";
$def[2] = "DEF:size=$RRDFILE[2]:$DS[2]:MAX " ;
$def[2] .= "CDEF:queue_mb=size,1048576,/ ";
$def[2] .= "AREA:queue_mb#65ab0e:\"Megabytes\" ";
$def[2] .= "LINE:queue_mb#206a0e ";
$def[2] .= "GPRINT:queue_mb:MAX:\"%6.2lf MB max\\n\" ";

# geht nicht.
#$def[2] .= "DEF:size_avg=$RRDFILE[2]:$DS[2]:AVG " ;
#$def[2] .= "DEF:size_last=$RRDFILE[2]:$DS[2]:LAST " ;
#$def[2] .= "CDEF:queue_mb_avg=size_avg,1048576,/ ";
#$def[2] .= "CDEF:queue_mb_last=size_last,1048576,/ ";
#$def[2] .= "GPRINT:queue_mb:LAST:\"%6.2lf MB last\" ";
#$def[2] .= "GPRINT:queue_mb:AVERAGE:\"%6.2lf MB avg\" ";

?>
