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

$opt[1] = "--vertical-label 'ADDRESSES(MB)' -X0 --upper-limit " . $MAX[1] . " -l0  --title \"Vmalloc address space of $hostname\" ";

$def[1] =  "DEF:used=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "DEF:chunk=$RRDFILE[2]:$DS[2]:MAX " ;
$def[1] .= "HRULE:$MAX[1]#000080:\"Vmalloc total\" ";
$def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning (used)\" ";
$def[1] .= "HRULE:$CRIT[1]#FF0000:\"Critical (used)\" ";

$def[1] .= "'COMMENT:\\n' ";
$def[1] .= "AREA:used#20cf80:\"used address space   \" " ;
$def[1] .= "GPRINT:used:LAST:\"%6.0lf MB last\" " ;
$def[1] .= "GPRINT:used:AVERAGE:\"%6.0lf MB avg\" " ;
$def[1] .= "GPRINT:used:MAX:\"%6.0lf MB max\\n\" ";

$def[1] .= "AREA:chunk#d0d0d0:\"largest free chunk   \":STACK " ;
$def[1] .= "GPRINT:chunk:LAST:\"%6.0lf MB last\" " ;
$def[1] .= "GPRINT:chunk:AVERAGE:\"%6.0lf MB avg\" " ;
$def[1] .= "GPRINT:chunk:MAX:\"%6.0lf MB max\\n\" " ;

$def[1] .= "LINE:used#00af60:\"\" " ;

?>
