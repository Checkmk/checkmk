<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$opt[1] = "--vertical-label 'Memory (Bytes)' --upper-limit " . $MAX[1] . " -l0  --title \"Memory usage of $hostname\" ";

$total_gb = $MAX[1] / 1073741824.0;
$total_text = sprintf("%.2fGB", $total_gb);

$def[1] =  "DEF:used=$RRDFILE[1]:$DS[1]:MAX "
         . "CDEF:usedgb=used,1073741824,/ "
         . "HRULE:$MAX[1]#000080:\"Total memory\: $total_text\" ";
if ($WARN[1]) {
       $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning (used)\" "
         . "HRULE:$CRIT[1]#FF0000:\"Critical (used)\" ";
}

$def[1] .= "'COMMENT:\\n' "
         . "AREA:used#20cf80:\"Used main memory   \" "
         . "GPRINT:usedgb:LAST:\"%6.2lf GB last\" "
         . "GPRINT:usedgb:AVERAGE:\"%6.2lf GB avg\" "
         . "GPRINT:usedgb:MAX:\"%6.2lf GB max\\n\" "
         ;


$def[1] .= "LINE:used#00af60:\"\" " ;

?>
