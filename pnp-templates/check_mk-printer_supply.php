<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
