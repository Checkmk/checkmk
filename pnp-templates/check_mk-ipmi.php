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

if ($UNIT[1] == 'degrees_C') {
    $unit   = "°C";
    $vlabel = "--vertical-label 'Celsius'";
} elseif ($UNIT[1] == 'unspecified') {
    $unit   = "";
    $vlabel = "";
} else {
    $unit   = $UNIT[1];
    $vlabel = "--vertical-label '$UNIT[1]'";
}

$opt[1] = "$vlabel -l0 --title \"IPMI sensor $NAME[1] / $hostname\" ";

$def[1] = "DEF:value=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "AREA:value#ffd040:\"Sensor $NAME[1]\" ";
$def[1] .= "LINE:value#ff8000 ";
$def[1] .= "GPRINT:value:LAST:\"%6.2lf $unit last\" " ;
$def[1] .= "GPRINT:value:AVERAGE:\"%6.2lf $unit avg\" " ;
$def[1] .= "GPRINT:value:MAX:\"%6.2lf $unit max\\n\" ";

?>
