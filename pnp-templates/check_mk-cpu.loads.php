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
