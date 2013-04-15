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

# Do not depend on numbers, use names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

$num_threads = $MAX[1];
$warnthreads = $WARN[1] * $num_threads / 100.0;
$critthreads = $CRIT[1] * $num_threads / 100.0;
$rightscale = 100.0 / $num_threads;

$opt[1] = "--vertical-label 'Used CPU threads' --right-axis $rightscale:0 --right-axis-format '%4.1lf%%' --right-axis-label 'Utilization %' -l0  -ru $num_threads --title \"CPU Utilization for $hostname ($num_threads CPU threads)\" ";

$def[1] =  "DEF:perc=$RRD[util] "
         . "CDEF:util=perc,$num_threads,*,100,/ "
         ;
         
$def[1] .= "HRULE:$MAX[util]#0040d0:\"$num_threads CPU Threads\\n\" "
         ;

$def[1] .= "AREA:util#60f020:\"Utilization\:\" "
         . "LINE:util#50b01a "
         . "GPRINT:perc:LAST:\"%.1lf%%\" "
         . "GPRINT:util:LAST:\"(%.1lf Threads) \" "
         . "GPRINT:perc:MIN:\"min\: %.1lf%%,\" "
         . "GPRINT:util:MIN:\"(%.1lf), \" "
         . "GPRINT:perc:MAX:\"max\: %.1lf%%\" "
         . "GPRINT:util:MAX:\"(%.1lf)\\n\" "
         ;


if (isset($RRD["avg"])) {
    $def[1] .= "DEF:aperc=$RRD[avg] ". 
               "CDEF:avg=aperc,$num_threads,*,100,/ ".
               "LINE:avg#004000:\"Averaged\:   \" ".
               "GPRINT:aperc:LAST:\"%.1lf%%,\" ".
               "GPRINT:aperc:MIN:\"min\: %.1lf%%,\" ".
               "GPRINT:aperc:MAX:\"max\: %.1lf%%\\n\" ".
               "";
}

if ($WARN['util']) {
    $def[1] .= "HRULE:$warnthreads#fff000:\"Warn at $WARN[util]%    \" "
            . "HRULE:$critthreads#ff0000:\"Critical at $CRIT[util]%\\n\" ";
}
else {
    $def[1] .= "COMMENT:\"\\n\" ";
}

?>
