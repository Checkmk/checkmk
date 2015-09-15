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

$opt[1] = "--vertical-label \"CPU utilization %\"  -l0  --title \"CPU utilization for $hostname\" ";
#
$def[1] =  "DEF:util1=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "AREA:util1#60C080:\"Avg. utilization last minute    \" " ;
$def[1] .= "GPRINT:util1:LAST:\"%6.0lf%% last\" " ;
$def[1] .= "GPRINT:util1:AVERAGE:\"%6.0lf%% avg\" " ;
$def[1] .= "GPRINT:util1:MAX:\"%6.0lf%% max\\n\" ";
$def[1] .= "DEF:util15=$RRDFILE[2]:$DS[1]:MAX " ;
$def[1] .= "LINE:util15#306040:\"Avg. utilization last 15 minutes\" " ;
$def[1] .= "GPRINT:util15:LAST:\"%6.0lf%% last\" " ;
$def[1] .= "GPRINT:util15:AVERAGE:\"%6.0lf%% avg\" " ;
$def[1] .= "GPRINT:util15:MAX:\"%6.0lf%% max\\n\" ";
$def[1] .= "HRULE:$WARN[1]#FFFF00 ";
$def[1] .= "HRULE:$CRIT[1]#FF0000 ";
?>
