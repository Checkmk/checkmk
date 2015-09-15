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

# Template contributed by Oliver Borgmann, Copyright 2010

$CRITPERC = $CRIT[1]*100/$MAX[1];
$WARNPERC = $WARN[1]*100/$MAX[1];

$opt[1] = "--vertical-label \"Percent left\" -l -20 -u 100 --title \"$hostname / $servicedesc  \" ";

if(preg_match('/black/i', $servicedesc))
  $color = '000000';
elseif(preg_match('/magenta/i', $servicedesc))
  $color = 'fc00ff';
elseif(preg_match('/yellow/i', $servicedesc))
  $color = 'ffff00';
elseif(preg_match('/cyan/i', $servicedesc))
  $color = '00ffff';
else
  $color = 'cccccc';

$def[1] = "DEF:var1=$RRDFILE[1]:$DS[1]:MAX ";
$def[1] .= "CDEF:perc1=var1,100,* ";
$def[1] .= "CDEF:perc=perc1,$MAX[1],/ ";
$def[1] .= "HRULE:$CRITPERC#ff0000:\"Crit\: $CRITPERC%\" ";
$def[1] .= "HRULE:$WARNPERC#ffff00:\"Warn\: $WARNPERC%\" ";
$def[1] .= "AREA:perc#$color:\"Percent\:\" ";
$def[1] .= "GPRINT:perc:MAX:\"%2.0lf%%\\n\" ";
?>
