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

$desc = str_replace("_", " ", $servicedesc);
$opt[1] = "-X0 --vertical-label \"Response Time (ms)\"  --title \"$hostname / $desc\" ";

$def[1] = ""
 . "DEF:var1=$RRDFILE[1]:$DS[1]:MAX "
 . "CDEF:ms=var1,1000,* "
 . "AREA:ms#66ccff:\"Response Time \" "
 . "LINE1:ms#000000:\"\" "
 . "GPRINT:ms:LAST:\"%3.3lg ms LAST \" "
 . "GPRINT:ms:MAX:\"%3.3lg ms MAX \" "
 . "GPRINT:ms:AVERAGE:\"%3.3lg ms AVERAGE \" "
;

$opt[2] = "--vertical-label \"Size (Bytes)\" --title \"Size of response\" ";
$def[2] =  ""
  . "DEF:size=$RRDFILE[2]:$DS[2]:AVERAGE " ;
if ($WARN[2] != "")
    $def[2] .= "HRULE:$WARN[2]#FFFF00 ";
if ($CRIT[2] != "")
    $def[2] .= "HRULE:$CRIT[2]#FF0000 ";
$def[2] .= ""
 . "AREA:size#cc66ff:\"Size of response \" "
 . "LINE1:size#000000:\"\" "
 . "GPRINT:size:LAST:\"%3.0lf Bytes LAST \" "
 . "GPRINT:size:MAX:\"%3.0lf Bytes MAX \" "
 . "GPRINT:size:AVERAGE:\"%3.0lf Bytes AVERAGE \" "
;

?>
