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

$desc = str_replace("_", " ", $servicedesc);

$opt[1] = "--vertical-label 'CPU utilization %' -l0  -u 100 --title \"CPU Utilization $hostname $desc\" ";
#
$def[1] =  "DEF:util=$RRDFILE[1]:$DS[1]:MAX ".
           "CDEF:ok=util,$WARN[1],MIN ".
           "CDEF:warn=util,$CRIT[1],MIN ".
           "AREA:util#c0f020 ".
           "AREA:warn#90f020 ".
           "AREA:ok#60f020:\"Utilization\:\" ".
           "LINE:util#40a018 ".
           "GPRINT:util:LAST:\"%.0lf%%,\" ".
           "GPRINT:util:MIN:\"min\: %.0lf%%,\" ".
           "GPRINT:util:MAX:\"max\: %.0lf%%\" ".
           "HRULE:$WARN[1]#ffe000:\"Warning at $WARN[1]%\" ".
           "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1]%\\n\" ".
           "";

?>
