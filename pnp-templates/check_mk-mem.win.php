<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

$maxmem = $MAX["memory"] / 1024.0;
$maxmemprint  = sprintf("%5.2f", $maxmem);
$maxpage = $MAX["pagefile"] / 1024.0;
$maxpageprint = sprintf("%5.2f", $maxpage);

$opt[1] = " --vertical-label 'Gigabytes' -X0 "
        . " -u " . ($maxmem * 120 / 100)
        . " -l " . ($maxpage * -120 / 100)
        . " --title \"Memory and page file usage $hostname\" ";


$def[1] = "DEF:mem=$RRD[memory] "
        . "CDEF:memgb=mem,1024,/ "
        . "DEF:page=$RRD[pagefile] "
        . "CDEF:pagegb=page,1024,/ "
        . "CDEF:mpagegb=pagegb,-1,* "

        . "AREA:$maxmem#b0ffe0:\"$maxmemprint GB RAM      \" "
        . "AREA:memgb#40f090 "
        . "GPRINT:memgb:LAST:\"%5.2lf GB last\" "
        . "GPRINT:memgb:AVERAGE:\"%5.2lf GB avg\" "
        . "GPRINT:memgb:MAX:\"%5.2lf GB max\" "
        . "HRULE:".($WARN["memory"]/1024)."#FFFF00:\"Warn\" "
        . "HRULE:".($CRIT["memory"]/1024)."#FF0000:\"Crit\\n\" "

        . "AREA:\"-$maxpage\"#b0e0f0:\"$maxpageprint GB page file\" "
        . "AREA:mpagegb#90b0ff "
        . "GPRINT:pagegb:LAST:\"%5.2lf GB last\" "
        . "GPRINT:pagegb:AVERAGE:\"%5.2lf GB avg\" "
        . "GPRINT:pagegb:MAX:\"%5.2lf GB max\" "
        . "HRULE:".(-$WARN["pagefile"]/1024)."#FFFF00:\"Warn\" "
        . "HRULE:".(-$CRIT["pagefile"]/1024)."#FF0000:\"Crit\\n\" "
        ;

# If averaging is enabled then we get two further metrics
if (isset($RRD["memory_avg"])) {
    $def[1] .= ""
        . "DEF:memavg=$RRD[memory_avg] "
        . "CDEF:memavggb=memavg,1024,/ "
        . "LINE:memavggb#006000:\"Memory Average     \" "
        . "DEF:pageavg=$RRD[pagefile_avg] "
        . "CDEF:pageavggb=pageavg,1024,/ "
        . "CDEF:mpageavggb=pageavggb,-1,* "
        . "LINE:mpageavggb#000060:\"Pagefile Average\\n\" "
        ;
}

?>
