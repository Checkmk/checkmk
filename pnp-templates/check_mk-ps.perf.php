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


# 1. Graph: Number of processes
$vertical = "count";
$format = "%3.0lf";
$upto = max(20, $CRIT["count"]);
$color = "8040f0";
$line = "202060";

$opt[1] = " --vertical-label \"count\" -X0 -L5 -l 0 -u $upto --title \"Number of Processes\" ";

$def[1] = ""
 . "DEF:count=$RRD[count] "
 . "AREA:count#$color:\"Processes\"     "
 . "LINE1:count#$line:\"\" "
 . "GPRINT:count:LAST:\"Current\: $format\" "
 . "GPRINT:count:MAX:\"Maximum\: $format \" "
 . "HRULE:$WARN[count]#FFFF00:\"Warning at $WARN[count]\" "
 . "HRULE:$CRIT[count]#FF0000:\"Critical at $CRIT[count]\" "
 ;

# 2. Graph: Memory usage
if (isset($RRD["vsz"])) {
 $opt[2] = " --vertical-label \"MB\" -l 0 --title \"Memory Usage per process\" ";
 $def[2] = ""
   . "DEF:count=$RRD[count] "
   . "DEF:vsz=$RRD[vsz] "
   . "DEF:rss=$RRD[rss] "
   . "CDEF:vszmb=vsz,1024,/,count,/ "
   . "CDEF:rssmb=rss,1024,/,count,/ "
   . "AREA:vszmb#90a0f0:\"Virtual size \" "
   . "GPRINT:vszmb:LAST:\"Current\: %5.1lf MB\" "
   . "GPRINT:vszmb:MIN:\"Min\: %5.1lf MB\" "
   . "GPRINT:vszmb:MAX:\"Max\: %5.1lf MB\" "
   . "AREA:rssmb#2070ff:\"Resident size\" "
   . "GPRINT:rssmb:LAST:\"Current\: %5.1lf MB\" "
   . "GPRINT:rssmb:MIN:\"Min\: %5.1lf MB\" "
   . "GPRINT:rssmb:MAX:\"Max\: %5.1lf MB\" "
   ;
}

if (isset($RRD["pcpu"])) {
    $opt[3] = " --vertical-label \"CPU(%)\" -l 0 -u 100 --title \"CPU Usage\" ";
    $def[3] = ""
     . "DEF:pcpu=$RRD[pcpu] "
     . "AREA:pcpu#30ff80:\"CPU usage (%) \" "
     . "LINE:pcpu#20a060:\"\" "
     . "GPRINT:pcpu:LAST:\"Current\: %4.1lf%%\" "
     . "GPRINT:pcpu:MIN:\"Min\: %4.1lf%%\" "
     . "GPRINT:pcpu:MAX:\"Max\: %4.1lf%%\\n\" ";

    if ($WARN['pcpu'] != '')
        $def[3] .= "HRULE:$WARN[pcpu]#FFFF00:\"Warning at $WARN[pcpu]%\" ";
    if ($CRIT['pcpu'] != '')
        $def[3] .= "HRULE:$CRIT[pcpu]#FF0000:\"Critical at $CRIT[pcpu]%\" ";

    if (isset($RRD["pcpuavg"])) {
        $def[3] .= "DEF:pcpuavg=$RRD[pcpuavg] 
                   LINE:pcpuavg#000000:\"Average over $MAX[pcpuavg] minutes\\n\" "; 
    }
}

?>
