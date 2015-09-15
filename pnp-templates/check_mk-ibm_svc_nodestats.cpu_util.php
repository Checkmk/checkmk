<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

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

$opt[1] = "--vertical-label 'Utilization %' -l0 -u 100 --title \"$hostname / $servicedesc\" ";

$def[1] =  "DEF:perc=$RRD[util] "
         . "CDEF:util=perc,$num_threads,*,100,/ "
         ;

$def[1] .= "AREA:util#60f020:\"Utilization\:\" "
         . "LINE:util#50b01a "
         . "GPRINT:perc:LAST:\"%.1lf%%\" "
         . "GPRINT:perc:MIN:\"min\: %.1lf%%\" "
         . "GPRINT:perc:MAX:\"max\: %.1lf%%\\n\" "
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
    $def[1] .= "HRULE:$WARN[1]#fff000:\"Warn at $WARN[util]%    \" "
            . "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[util]%\\n\" ";
}
else {
    $def[1] .= "COMMENT:\"\\n\" ";
}

?>
