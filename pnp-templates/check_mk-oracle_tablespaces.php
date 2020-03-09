<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$title = str_replace("_", " ", $servicedesc);


$opt[1] = "--vertical-label 'GB' -l0 --title \"$title\" ";
#
$def[1] =  "DEF:current=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:used=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "DEF:max=$RRDFILE[3]:$DS[3]:MAX " ;
$def[1] .= "CDEF:current_gb=current,1073741824.0,/ ";
$def[1] .= "CDEF:max_gb=max,1073741824.0,/ ";
$def[1] .= "CDEF:used_gb=used,1073741824.0,/ ";

$def[1] .= "AREA:max_gb#80c0ff:\"Maximum size\" " ;
$def[1] .= "LINE:max_gb#6080c0:\"\" " ;
$def[1] .= "GPRINT:max_gb:LAST:\"%2.2lfGB\" ";
$def[1] .= "AREA:current_gb#00ff80:\"Current size\" " ;
$def[1] .= "LINE:current_gb#008040:\"\" " ;
$def[1] .= "GPRINT:current_gb:LAST:\"%2.2lfGB\" ";
$def[1] .= "AREA:used_gb#f0b000:\"Used by user data\" " ;
$def[1] .= "LINE:used_gb#806000:\"\" " ;
$def[1] .= "GPRINT:used_gb:LAST:\"%2.2lfGB\" ";

?>
