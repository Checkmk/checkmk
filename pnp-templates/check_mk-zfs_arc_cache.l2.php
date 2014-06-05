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

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

#
# hit_ratio
#

$ds_name[1] = "L2 Cache Hit Ratio";
$opt[1]  = "--vertical-label '%' -l0 --title \"L2 Cache Hit Ratio for $hostname / $servicedesc\" ";
$def[1]  = "DEF:hit_ratio=".$RRD['l2_hit_ratio']." ";
$def[1] .= "LINE:hit_ratio#408000:\"L2 Cache Hit Ratio        \" ";
$def[1] .= "GPRINT:hit_ratio:LAST:\"last %2.2lf %%\" ";
$def[1] .= "GPRINT:hit_ratio:AVERAGE:\"avg %2.2lf %%\" ";
$def[1] .= "GPRINT:hit_ratio:MIN:\"min %2.2lf %%\" ";
$def[1] .= "GPRINT:hit_ratio:MAX:\"max %2.2lf %%\\n\" ";

#
# size
#

$ds_name[2] = "L2 Cache Size";
$opt[2]  = "--vertical-label 'Bytes' -l0 --title \"L2 Cache Size for $hostname / $servicedesc\" ";
$def[2]  = "DEF:size=".$RRD['l2_size']." ";
$def[2] .= "AREA:size#408000:\"L2 Cache Size\" ";
$def[2] .= "LINE:size#000000 ";
$def[2] .= "GPRINT:size:LAST:\"last %2.0lf Bytes\" ";
$def[2] .= "GPRINT:size:AVERAGE:\"avg %2.0lf Bytes\\n\" ";
$def[2] .= "GPRINT:size:MIN:\"                 min  %2.0lf Bytes\" ";
$def[2] .= "GPRINT:size:MAX:\"max %2.0lf Bytes\\n\" ";

?>
