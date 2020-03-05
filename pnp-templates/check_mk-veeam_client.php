<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'Bytes' -l 0  --title '$hostname: Total Size of Backup' ";

$def[1] = "DEF:mb=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:var1=mb,1048576,/ ";
$def[1] .= "AREA:mb#d080af:\"Total Size \" ";
$def[1] .= "LINE1:mb#d020a0: ";
$def[1] .= "GPRINT:var1:LAST:\"last\: %8.1lf MB\" ";
$def[1] .= "GPRINT:var1:MAX:\"max\: %8.1lf MB \" ";

$opt[2] = "--vertical-label 'time (sec)' -l 0 -X 0 --title '$hostname: Duration of Backup' ";

$def[2] = "DEF:duration=$RRDFILE[2]:$DS[1]:MAX ";
$def[2] .= "AREA:duration#d080af:\"duration \" ";
$def[2] .= "LINE1:duration#d020a0: ";
$def[2] .= "GPRINT:duration:LAST:\"last\: %8.1lf s\" ";
$def[2] .= "GPRINT:duration:MAX:\"max\: %8.1lf s \" ";
$def[2] .= "GPRINT:duration:AVERAGE:\"avg\: %8.1lf s\\n\" ";

$opt[3] = "--vertical-label 'Bytes/sec' -l 0  --title '$hostname: Average Speed of Backup' ";
$def[3] = "DEF:avgspeed=$RRDFILE[3]:$DS[1]:MAX ";
$def[3] .= "CDEF:var2=avgspeed,1048576,/ ";
$def[3] .= "LINE1:avgspeed#d020a0:\"thruput\" ";
$def[3] .= "GPRINT:var2:LAST:\"   last\: %8.2lf MB/s\" ";
$def[3] .= "GPRINT:var2:MAX:\"max\: %8.2lf MB/s \" ";
$def[3] .= "GPRINT:var2:AVERAGE:\"avg\: %8.2lf MB/s\\n\" ";

?>
