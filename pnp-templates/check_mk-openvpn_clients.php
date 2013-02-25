<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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

