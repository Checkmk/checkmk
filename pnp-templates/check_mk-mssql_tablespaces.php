<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$title = str_replace("_", " ", $servicedesc);

$opt[1] = "--vertical-label 'Bytes' -l0 --title \"$title\" ";
#
$def[1] =  "DEF:size=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:unallocated=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "DEF:data=$RRDFILE[4]:$DS[4]:MAX " ;
$def[1] .= "DEF:indexes=$RRDFILE[5]:$DS[5]:MAX " ;
$def[1] .= "DEF:unused=$RRDFILE[6]:$DS[6]:MAX " ;

$def[1] .= "AREA:size#f7f7f7:\"Size    \" " ;
$def[1] .= "LINE:size#000000 " ;
$def[1] .= "GPRINT:size:LAST:\"%4.2lf%sB\" ";

$def[1] .= "AREA:data#80c0ff:\"Data       \" " ;
$def[1] .= "LINE:data#6080c0:\"\" " ;
$def[1] .= "GPRINT:data:LAST:\"%4.2lf%sB\" ";

$def[1] .= "AREA:indexes#00ff80:\"Indexes\":STACK " ;
$def[1] .= "GPRINT:indexes:LAST:\"%4.2lf%sB\\n\" ";

$def[1] .= "AREA:unused#f0b000:\"Unused\":STACK " ;
$def[1] .= "GPRINT:unused:LAST:\"%4.2lf%sB\" ";

$def[1] .= "AREA:unallocated#dfdfdf:\"Unallocated\":STACK " ;
$def[1] .= "GPRINT:unallocated:LAST:\"%4.2lf%sB\\n\" ";


?>
