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
