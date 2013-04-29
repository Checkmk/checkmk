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

$desc = str_replace("_", " ", $servicedesc);
$opt[1] = "--vertical-label 'CPU utilization %' -l0  -u 100 --title \"$hostname - $desc\" ";

$def[1] =  "DEF:util=$RRD[util] ". 
           "AREA:util#60f020:\"Utilization\:\" ".
           "LINE:util#40a018 ".
           "GPRINT:util:LAST:\"%4.1lf%%,\" ".
           "GPRINT:util:MIN:\"min\: %4.1lf%%,\" ".
           "GPRINT:util:MAX:\"max\: %4.1lf%%\\n\" ".
           "";

if (isset($RRD["avg"])) {
    $def[1] .= "DEF:avg=$RRD[avg] ". 
               "LINE:avg#000080:\"Averaged    \" ".
               "GPRINT:avg:LAST:\"%4.1lf%%,\" ".
               "GPRINT:avg:MIN:\"min\: %4.1lf%%,\" ".
               "GPRINT:avg:MAX:\"max\: %4.1lf%%\\n\" ".
               "";
}

if ($WARN[1]) {
    $def[1] .= 
           "HRULE:$WARN[1]#ffe000:\"Warning at $WARN[1]%\" ".
           "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1]%\\n\" ".
           "";
}
#

?>
