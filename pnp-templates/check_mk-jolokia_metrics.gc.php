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


$opt[1] = "--vertical-label \"GC Count\"  --title \" $servicedesc for $hostname\" ";

$def[1] =  "DEF:c=$RRDFILE[1]:$DS[1]:AVERAGE ";

$def[1] .= rrd::comment("$NAME[1]\: \\n");
$def[1] .= "AREA:c#3bfcdf:\"\" " ;
$def[1] .= "LINE1:c#00b499:\"GC Count per Minute\" " ;
$def[1] .= "GPRINT:c:LAST:\"%3.4lg LAST \" ";
$def[1] .= "GPRINT:c:AVERAGE:\"%3.4lg AVERAGE \" ";
$def[1] .= "GPRINT:c:MAX:\"%3.4lg MAX \\n\" ";

if ($WARN[1] != "") {
   $def[1] .= "HRULE:$WARN[1]#FFFF00:\"Warning  at $WARN[1]$UNIT[1] \\n\" ";
}
if ($CRIT[1] != "") {
   $def[1] .= "HRULE:$CRIT[1]#FF0000:\"Critical at $CRIT[1]$UNIT[1]  \\n\" ";
}

$opt[2] = "--vertical-label \"GC Time\"  --title \" $servicedesc for $hostname\" ";

$def[2] =  "DEF:t=$RRDFILE[2]:$DS[2]:AVERAGE ";

$def[2] .= rrd::comment("$NAME[2]\: \\n");
$def[2] .= "AREA:t#ffc7ac:\"\" " ;
$def[2] .= "LINE1:t#ff6d25:\"GC Time (ms) per Minute\" " ;
$def[2] .= "GPRINT:t:LAST:\"%3.0lf$UNIT[2] LAST \" ";
$def[2] .= "GPRINT:t:AVERAGE:\"%3.2lf$UNIT[2] AVERAGE \" ";
$def[2] .= "GPRINT:t:MAX:\"%3.2lf$UNIT[2] MAX \\n\" ";
if ($WARN[2] != "") {
   $def[2] .= "HRULE:$WARN[2]#FFFF00:\"Warning  at $WARN[2]$UNIT[2] \\n\" ";
}
if ($CRIT[2] != "") {
   $def[2] .= "HRULE:$CRIT[2]#FF0000:\"Critical at $CRIT[2]$UNIT[2]  \\n\" ";
}
?>
