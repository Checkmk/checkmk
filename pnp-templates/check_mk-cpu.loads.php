<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The number of data source various due to different
# settings (such as averaging). We rather work with names
# than with numbers.
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

$title = "CPU Load for $hostname";
if ($MAX[1]) {
    $title .= " - $MAX[1] CPU Cores";
}

$opt[1] = "--vertical-label 'Load average' -l0  -u 1 --title \"$title\" ";

$def[1] =  ""
         . "DEF:load1=$RRD[load1] "
         . "AREA:load1#60c0e0:\"Load average  1 min \" "
         . "GPRINT:load1:LAST:\"%6.2lf last\" "
         . "GPRINT:load1:AVERAGE:\"%6.2lf avg\" "
         . "GPRINT:load1:MAX:\"%6.2lf max\\n\" "

         . "DEF:load15=$RRD[load15] "
         . "LINE:load15#004080:\"Load average 15 min \" "
         . "GPRINT:load15:LAST:\"%6.2lf last\" "
         . "GPRINT:load15:AVERAGE:\"%6.2lf avg\" "
         . "GPRINT:load15:MAX:\"%6.2lf max\\n\" "
         . "";

if ($WARN[1]) {
    $def[1] .= ""
         . "HRULE:$WARN[1]#FFFF00 "
         . "HRULE:$CRIT[1]#FF0000 "
         . "";
}


if (isset($RRD["predict_load15"])) {
    $def[1] .= ""
         . "DEF:predict=$RRD[predict_load15] "
         . "LINE:predict#ff0000:\"Reference for prediction \\n\" "
         . "";
}
?>
