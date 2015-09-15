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

$opt[1] = "--vertical-label '%' -l0  -u 100 --title \"CPU Utilization\" ";
#
$def[1]  =  "DEF:util1=$RRDFILE[1]:$DS[1]:AVERAGE " ;
$def[1] .=  "DEF:util5=$RRDFILE[2]:$DS[1]:AVERAGE " ;
$def[1] .=  "DEF:util60=$RRDFILE[3]:$DS[1]:AVERAGE " ;
$def[1] .=  "DEF:util300=$RRDFILE[4]:$DS[1]:AVERAGE " ;

$def[1] .= "AREA:util60#60f020:\"Utilization 60s\" " ;
$def[1] .= "GPRINT:util60:MIN:\"Min\: %2.1lf%%\" " ;
$def[1] .= "GPRINT:util60:MAX:\"Max\: %2.1lf%%\" " ;
$def[1] .= "GPRINT:util60:LAST:\"Last\: %2.1lf%%\" " ;
$def[1] .= "HRULE:$WARN[3]#FFFF00:\"Warn\" " ;
$def[1] .= "HRULE:$CRIT[3]#FF0000:\"Crit\\n\" " ;

$def[1] .= "LINE:util1#000000:\"Util 1s \" " ;
$def[1] .= "GPRINT:util1:LAST:\"Last\: %2.1lf%%\" " ;

$def[1] .= "LINE:util5#0000ff:\"5s \" " ;
$def[1] .= "GPRINT:util5:LAST:\"Last\: %2.1lf%%\" " ;

$def[1] .= "LINE:util300#ff00ff:\"300s \" " ;
$def[1] .= "GPRINT:util300:LAST:\"Last\: %2.1lf%%\\n\" " ;
?>
