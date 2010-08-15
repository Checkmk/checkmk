<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

# Graph 1: used bandwidth
$bbandwidth = $MAX[1];
$bandwidth = $bbandwidth;
$bwuom = '';
if($bandwidth > 1024 * 1024 * 1024) {
	$bandwidth /= 1024 * 1024 * 1024;
	$bwuom = 'G';
} elseif($bandwidth > 1024 * 1024) {
	$bandwidth /= 1024 * 1024;
	$bwuom = 'M';
} elseif($bandwidth > 1024) {
	$bandwidth /= 1024;
	$bwuom = 'K';
}

$ds_name[1] = 'QoS Class Traffic';
$opt[1] = "--vertical-label \"MB/sec\" -X0 -b 1024 -l -1 -u 1 --title \"$hostname / $servicedesc\" ";
$def[1] = 
  "HRULE:0#c0c0c0 ".
  "HRULE:$bbandwidth#808080:\"Interface speed\:  " . sprintf("%.1f", $bandwidth) . " ".$bwuom."B/s\\n\" ".
  "HRULE:-$bbandwidth#808080: ".
  "DEF:postbytes=$RRDFILE[1]:$DS[1]:MAX ".
  "DEF:dropbytes=$RRDFILE[2]:$DS[2]:MAX ".
  "CDEF:postmb=postbytes,1048576,/ ".
  "CDEF:dropmb=dropbytes,1048576,/ ".
  "AREA:postmb#00e060:\"post        \" ".
  "GPRINT:postbytes:LAST:\"%5.1lf %sB/s last\" ".
  "GPRINT:postbytes:AVERAGE:\"%5.1lf %sB/s avg\" ".
  "GPRINT:postbytes:MAX:\"%5.1lf %sB/s max\\n\" ".
  "AREA:dropmb#0080e0:\"drop        \" ".
  "GPRINT:dropbytes:LAST:\"%5.1lf %sB/s last\" ".
  "GPRINT:dropbytes:AVERAGE:\"%5.1lf %sB/s avg\" ".
  "GPRINT:dropbytes:MAX:\"%5.1lf %sB/s max\\n\" ";

?>
