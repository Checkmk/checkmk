<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'Througput (MByte/s)' -l0  -u 1 --title \"Disk throughput $hostname / $servicedesc\" ";

$def[1]  = "DEF:bytes=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "CDEF:mb=bytes,1048576,/ " ;
$def[1] .= "AREA:mb#40c080 " ;
$def[1] .= "GPRINT:mb:LAST:\"%6.1lf MByte/s last\" " ;
$def[1] .= "GPRINT:mb:AVERAGE:\"%6.1lf MByte/s avg\" " ;
$def[1] .= "GPRINT:mb:MAX:\"%6.1lf MByte/s max\\n\" ";
?>
