<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'CPU utilization %' -l0  -u 100 --title \"CPU Utilization for $hostname\" ";

$def[1] =  "DEF:user=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:system=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "DEF:wait=$RRDFILE[3]:$DS[3]:AVERAGE " ;
$def[1] .= "CDEF:us=user,system,+ ";
$def[1] .= "CDEF:sum=us,wait,+ ";
$def[1] .= "CDEF:idle=100,sum,- ";


$def[1] .= "LINE:idle#ffffff:\"Idle\" " ;
$def[1] .= "GPRINT:idle:LAST:\"%2.1lf%%\" " ;

$def[1] .= "AREA:system#ff6000:\"System\" " ;
$def[1] .= "GPRINT:system:LAST:\"%2.1lf%%\" " ;

$def[1] .= "AREA:user#60f020:\"User\":STACK " ;
$def[1] .= "GPRINT:user:LAST:\"%2.1lf%%\" " ;

$def[1] .= "AREA:wait#00b0c0:\"Wait\":STACK " ;
$def[1] .= "GPRINT:wait:LAST:\"%2.1lf%%\" " ;

$def[1] .= "LINE:sum#004080:\"Utilization\" " ;
$def[1] .= "GPRINT:sum:LAST:\"%2.1lf%%\" " ;

?>
