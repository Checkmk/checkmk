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

$opt[1] = "--vertical-label 'MEMORY(MB)' -X0 --upper-limit " . ($MAX[1] * 120 / 100) . " -l0  --title \"Memory usage $hostname\" ";

$maxgb = sprintf("%.1f", $MAX[1] / 1024.0);

$def[1] =  "DEF:ram=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:swap=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "DEF:virt=$RRDFILE[3]:$DS[3]:MAX " ;
$def[1] .= "HRULE:$MAX[3]#000080:\"RAM+SWAP installed\" ";
$def[1] .= "HRULE:$MAX[1]#2040d0:\"$maxgb GB RAM installed\" ";
$def[1] .= "HRULE:$WARN[3]#FFFF00:\"Warning\" ";
$def[1] .= "HRULE:$CRIT[3]#FF0000:\"Critical\" ";

$def[1] .= "'COMMENT:\\n' ";
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

/* HACK: Avoid error if RRD does not contain two data
 sources which .XML file *does*. F..ck. This does not
 work with multiple RRDs... */
$retval = -1;
system("rrdtool info $RRDFILE[1] | fgrep -q 'ds[5]'", $retval);
if ($retval == 0)
{
 if (count($NAME) >= 4 and $NAME[4] == "mapped") {
   $def[1] .= "DEF:mapped=$RRDFILE[4]:$DS[4]:MAX " ;
   $def[1] .= "LINE2:mapped#8822ff:\"Memory mapped\" " ;
   $def[1] .= "GPRINT:mapped:LAST:\"%6.0lf MB last\" " ;
   $def[1] .= "GPRINT:mapped:AVERAGE:\"%6.0lf MB avg\" " ;
   $def[1] .= "GPRINT:mapped:MAX:\"%6.0lf MB max\\n\" " ;
  }

 if (count($NAME) >= 5 and $NAME[5] == "committed_as") {
   $def[1] .= "DEF:committed=$RRDFILE[5]:$DS[5]:MAX " ;
   $def[1] .= "LINE2:committed#cc00dd:\"Committed    \" " ;
   $def[1] .= "GPRINT:committed:LAST:\"%6.0lf MB last\" " ;
   $def[1] .= "GPRINT:committed:AVERAGE:\"%6.0lf MB avg\" " ;
   $def[1] .= "GPRINT:committed:MAX:\"%6.0lf MB max\\n\" " ;
  }
 }  

?>
