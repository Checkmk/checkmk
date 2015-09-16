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

# The number of data source various due to different
# settings (such as averaging). We rather work with names
# than with numbers.
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = $RRDFILE[$i].":".$DS[$i].":MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

$nr = 0;

# Paint graph for voltage, if check supports this

if (isset($RRD["voltage"])) {
    $nr++;
    $opt[$nr] = "--vertical-label 'Voltage (V)' --title \"Output voltage for $hostname / $servicedesc\" ";

    $def[$nr] = ""
       . "DEF:voltage=$RRD[voltage] "
       . "LINE:voltage#003377:\"Output voltage\" "
       . "GPRINT:voltage:LAST:\"%6.0lf V last\" "
       . "GPRINT:voltage:AVERAGE:\"%6.0lf V avg\" "
       . "GPRINT:voltage:MAX:\"%6.0lf V max\\n\" "
       . "HRULE:$WARN[voltage]#FFFF00:\"Warning\: $WARN[voltage] V\" "
       . "HRULE:$CRIT[voltage]#FF0000:\"Critical\: $CRIT[voltage] V\\n\" "
       . "";
}

# Paint graph for current, if check supports this

if (isset($RRD["current"])) {
    $nr++;
    $opt[$nr] = "--vertical-label 'Current (A)' --title \"Output current for $hostname / $servicedesc\" ";

    $def[$nr] = ""
       . "DEF:current=$RRD[current] "
       . "LINE:current#007733:\"Output current\" "
       . "GPRINT:current:LAST:\"%6.0lf A last\" "
       . "GPRINT:current:AVERAGE:\"%6.0lf A avg\" "
       . "GPRINT:current:MAX:\"%6.0lf A max\\n\" "
       . "";
}

# Paint graph for percentual load, if check supports this

if (isset($RRD["load"])) {
    $nr++;
    $opt[$nr] = "--vertical-label 'Load (%)' -l0 -u100 --title \"Output load for $hostname / $servicedesc\" ";

    $def[$nr] = ""
       . "DEF:load=$RRD[load] "
       . "AREA:load#8050ff:\"Output load\" "
       . "LINE:load#5030aa "
       . "GPRINT:load:LAST:\"%6.0lf %% last\" "
       . "GPRINT:load:AVERAGE:\"%6.0lf %% avg\" "
       . "GPRINT:load:MAX:\"%6.2lf %% max\\n\" "
       . "HRULE:$WARN[load]#FFFF00:\"Warning\: $WARN[load] %\" "
       . "HRULE:$CRIT[load]#FF0000:\"Critical\: $CRIT[load] %\\n\" "
       . "";
}
