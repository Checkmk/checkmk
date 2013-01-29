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

$opt[1] = "--vertical-label 'MEMORY(MB)' --upper-limit " . ($MAX[1] * 120 / 100) . " -l0  --title \"Memory usage $hostname\" ";

$def[1] =  "DEF:ram=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .= "DEF:swap=$RRDFILE[2]:$DS[2]:AVERAGE " ;
$def[1] .= "DEF:virt=$RRDFILE[3]:$DS[3]:AVERAGE " ;
$def[1] .= "HRULE:$MAX[3]#000080:\"RAM+SWAP installed\" ";
$def[1] .= "HRULE:$MAX[1]#2040d0:\"RAM installed\" ";
$def[1] .= "HRULE:$WARN[3]#FFFF00:\"Warning\" ";
$def[1] .= "HRULE:$CRIT[3]#FF0000:\"Critical\\n\" ";

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
