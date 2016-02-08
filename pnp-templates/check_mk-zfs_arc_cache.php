<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
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

$ds_name[1] = "Cache Hit Ratio";
$opt[1]  = "--vertical-label '%' -l0 --title \"Cache Hit Ratio for $hostname / $servicedesc\" ";
$def[1]  = "DEF:hit_ratio=".$RRD['hit_ratio']." ";
$def[1] .= "DEF:prefetch_data_hit_ratio=".$RRD['prefetch_data_hit_ratio']." ";
$def[1] .= "DEF:prefetch_metadata_hit_ratio=".$RRD['prefetch_metadata_hit_ratio']." ";
$def[1] .= "LINE:hit_ratio#408000:\"Hit Ratio        \" ";
$def[1] .= "GPRINT:hit_ratio:LAST:\"last %2.2lf %%\" ";
$def[1] .= "GPRINT:hit_ratio:AVERAGE:\"avg %2.2lf %%\" ";
$def[1] .= "GPRINT:hit_ratio:MIN:\"min %2.2lf %%\" ";
$def[1] .= "GPRINT:hit_ratio:MAX:\"max %2.2lf %%\\n\" ";
$def[1] .= "LINE:prefetch_data_hit_ratio#000080:\"Prefetch Data    \" ";
$def[1] .= "GPRINT:prefetch_data_hit_ratio:LAST:\"last %2.2lf %%\" ";
$def[1] .= "GPRINT:prefetch_data_hit_ratio:AVERAGE:\"avg %2.2lf %%\" ";
$def[1] .= "GPRINT:prefetch_data_hit_ratio:MIN:\"min %2.2lf %%\" ";
$def[1] .= "GPRINT:prefetch_data_hit_ratio:MAX:\"max %2.2lf %%\\n\" ";
$def[1] .= "LINE:prefetch_metadata_hit_ratio#800000:\"Prefetch Metadata\" ";
$def[1] .= "GPRINT:prefetch_metadata_hit_ratio:LAST:\"last %2.2lf %%\" ";
$def[1] .= "GPRINT:prefetch_metadata_hit_ratio:AVERAGE:\"avg %2.2lf %%\" ";
$def[1] .= "GPRINT:prefetch_metadata_hit_ratio:MIN:\"min %2.2lf %%\" ";
$def[1] .= "GPRINT:prefetch_metadata_hit_ratio:MAX:\"max %2.2lf %%\\n\" ";

#
# size
#

$ds_name[2] = "Cache Size";
$opt[2]  = "--vertical-label 'Bytes' -l0 --title \"Cache Size for $hostname / $servicedesc\" ";
$def[2]  = "DEF:size=".$RRD['size']." ";
$def[2] .= "AREA:size#408000:\"Cache Size\" ";
$def[2] .= "LINE:size#000000 ";
$def[2] .= "GPRINT:size:LAST:\"last %2.0lf Bytes\" ";
$def[2] .= "GPRINT:size:AVERAGE:\"avg %2.0lf Bytes\\n\" ";
$def[2] .= "GPRINT:size:MIN:\"              min  %2.0lf Bytes\" ";
$def[2] .= "GPRINT:size:MAX:\"max %2.0lf Bytes\\n\" ";

#
# arc meta
#

if( isset($RRD['arc_meta_used']) and isset($RRD['arc_meta_limit']) and isset($RRD['arc_meta_max'])) {
    $ds_name[3] = "Arc Meta";
    $opt[3]  = "--vertical-label 'Bytes' -l0 --title \"Arc Meta for $hostname / $servicedesc\" ";
    $def[3]  = "DEF:arc_meta_used=".$RRD['arc_meta_used']." ";
    $def[3] .= "DEF:arc_meta_limit=".$RRD['arc_meta_limit']." ";
    $def[3] .= "DEF:arc_meta_max=".$RRD['arc_meta_max']." ";
    $def[3] .= "LINE:arc_meta_used#408000:\"used  \" ";
    $def[3] .= "GPRINT:arc_meta_used:LAST:\"last %2.0lf Bytes\" ";
    $def[3] .= "GPRINT:arc_meta_used:AVERAGE:\"avg %2.0lf Bytes\\n\" ";
    $def[3] .= "LINE:arc_meta_limit#000080:\"limit \" ";
    $def[3] .= "GPRINT:arc_meta_limit:LAST:\"last %2.0lf Bytes\" ";
    $def[3] .= "GPRINT:arc_meta_limit:AVERAGE:\"avg %2.0lf Bytes\\n\" ";
    $def[3] .= "LINE:arc_meta_max#800000:\"max   \" ";
    $def[3] .= "GPRINT:arc_meta_max:LAST:\"last %2.0lf Bytes\" ";
    $def[3] .= "GPRINT:arc_meta_max:AVERAGE:\"avg %2.0lf Bytes\\n\" ";
}

?>
