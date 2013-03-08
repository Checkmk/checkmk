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

$bandwidth = $MAX[1]  * 8;
$warn      = $WARN[1] * 8;
$crit      = $CRIT[1] * 8;

$bwuom = '';
$base = 1000;
if($bandwidth > $base * $base * $base) {
	$warn /= $base * $base * $base;
	$crit /= $base * $base * $base;
	$bandwidth /= $base * $base * $base;
	$bwuom = 'G';
} elseif($bandwidth > $base * $base) {
	$warn /= $base * $base;
	$crit /= $base * $base;
	$bandwidth /= $base * $base;
	$bwuom = 'M';
} elseif($bandwidth > $base) {
	$warn /= $base;
	$crit /= $base;
	$bandwidth /= $base;
	$bwuom = 'K';
}

$ds_name[1] = 'QoS Class Traffic';
$opt[1] = "--vertical-label \"MBit/sec\" -X0 -b 1000 --title \"$hostname / $servicedesc\" ";
$def[1] = 
  "HRULE:0#c0c0c0 ".
  "HRULE:$bandwidth#808080:\"Interface speed\:  " . sprintf("%.1f", $bandwidth) . " ".$bwuom."Bit/s\\n\" ".
  "HRULE:$warn#FFE000:\"Warning\:          " . sprintf("%.1f", $warn) . " ".$bwuom."Bit/s\\n\" ".
  "HRULE:$crit#FF5030:\"Critical\:         " . sprintf("%.1f", $crit) . " ".$bwuom."Bit/s\\n\" ".
  "DEF:postbytes=$RRDFILE[1]:$DS[1]:MAX ".
  "DEF:dropbytes=$RRDFILE[2]:$DS[2]:MAX ".
  "CDEF:post_traffic=postbytes,8,* ".
  "CDEF:drop_traffic=dropbytes,8,* ".
  "CDEF:postmbit=post_traffic,1000000,/ ".
  "CDEF:dropmbit=drop_traffic,1000000,/ ".
  "AREA:postmbit#00e060:\"post        \" ".
  "GPRINT:post_traffic:LAST:\"%5.1lf %sBit/s last\" ".
  "GPRINT:post_traffic:AVERAGE:\"%5.1lf %sBit/s avg\" ".
  "GPRINT:post_traffic:MAX:\"%5.1lf %sBit/s max\\n\" ".
  "AREA:dropmbit#0080e0:\"drop        \" ".
  "GPRINT:drop_traffic:LAST:\"%5.1lf %sBit/s last\" ".
  "GPRINT:drop_traffic:AVERAGE:\"%5.1lf %sBit/s avg\" ".
  "GPRINT:drop_traffic:MAX:\"%5.1lf %sBit/s max\\n\" ";


if (isset($DS[3])) {
$def[1] .= "DEF:postbytes_avg=$RRDFILE[3]:$DS[1]:MAX ".
           "DEF:dropbytes_avg=$RRDFILE[4]:$DS[2]:MAX ".
           "CDEF:post_traffic_avg=postbytes_avg,8,* ".
           "CDEF:drop_traffic_avg=dropbytes_avg,8,* ".
           "CDEF:postmbit_avg=post_traffic_avg,1000000,/ ".
           "CDEF:dropmbit_avg=drop_traffic_avg,1000000,/ ".
           "LINE:postmbit_avg#3b762e:\"post avg    \" ".
           "GPRINT:post_traffic_avg:LAST:\"%5.1lf %sBit/s last\" ".
           "GPRINT:post_traffic_avg:AVERAGE:\"%5.1lf %sBit/s avg\" ".
           "GPRINT:post_traffic_avg:MAX:\"%5.1lf %sBit/s max\\n\" ".
           "LINE:dropmbit_avg#1255a9:\"drop avg    \" ".
           "GPRINT:drop_traffic_avg:LAST:\"%5.1lf %sBit/s last\" ".
           "GPRINT:drop_traffic_avg:AVERAGE:\"%5.1lf %sBit/s avg\" ".
           "GPRINT:drop_traffic_avg:MAX:\"%5.1lf %sBit/s max\\n\" ";
}


?>
