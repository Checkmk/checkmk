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

$title = str_replace("_", " ", substr($servicedesc, 10));
$vertical = "Number";
$format = "%4.0lf";
$color = "8040f0";
$line = "202060";

$opt[1] = " --vertical-label \"$vertical\" -X0 -L5 -l 0 -u $MAX[1] --title \"$title  \" ";

$def[1] = "DEF:var1=$RRDFILE[1]:$DS[1]:MAX ".
          "AREA:$MAX[1]#f3f3f2:\"\" ".
          "LINE:$MAX[1]#8b8989:\"Kernel threshold\" ".
          "AREA:var1#$color:\"$title\"     ".
          "LINE1:var1#$line:\"\" ".
          "GPRINT:var1:LAST:\"Current\: $format\" ".
          "GPRINT:var1:MAX:\"Peak\: $format  \" ".
          "";

# Add in warning / crit if they're passed to us.
if (isset($WARN[1]) and $WARN[1] != "") {
    $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning at $WARN[1]\" ".
               "HRULE:$CRIT[1]#FF0000:\"Critical at $CRIT[1]\" ";
    }

?>
