<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$parts = explode("_",$servicedesc);
$channel = $parts[2];

$opt[1] = "--vertical-label \"MBit per secound\" -X0 -l0  --title \"VPN-Traffic (raw) $hostname / $channel\" ";

$def[1] =  "DEF:in=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:out=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "CDEF:mb_out=out,131072,/ " ;
$def[1] .= "CDEF:mb_out_n=mb_out,-1,* " ;
$def[1] .= "CDEF:mb_in=in,131072,/ " ;
$def[1] .= "AREA:mb_in#30d050:\"Inbound  \" " ;
$def[1] .= "GPRINT:mb_in:LAST:\"%6.2lf MBit/s last\" " ;
$def[1] .= "GPRINT:mb_in:AVERAGE:\"%6.2lf MBit/s avg\" " ;
$def[1] .= "GPRINT:mb_in:MAX:\"%6.2lf MBit/s max\\n\" ";
$def[1] .= "AREA:mb_out_n#0060c0:\"Outbound \" " ;
$def[1] .= "GPRINT:mb_out:LAST:\"%6.2lf MBit/s last\" " ;
$def[1] .= "GPRINT:mb_out:AVERAGE:\"%6.2lf MBit/s avg\" " ;
$def[1] .= "GPRINT:mb_out:MAX:\"%6.2lf MBit/s max\\n\" " ;
?>

