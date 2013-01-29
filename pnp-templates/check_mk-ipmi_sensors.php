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

$parts = explode("_", $servicedesc);
$sensorname = implode(" ", $parts);

/* This is obsolete. ipmi_sensors does not longer send perfdata
   for fans... 
if ($parts[2] == "Fan")
{
	$opt[1] = "--vertical-label 'RPM' -X0 -l0 -u6000 --title \"$sensorname\" ";

	$def[1] = "DEF:rpm=$RRDFILE[1]:$DS[1]:MIN ";
	$def[1] .= "AREA:rpm#0080a0:\"Rotations per minute\" ";
	$def[1] .= "LINE:rpm#004060 ";
	$def[1] .= "HRULE:$CRIT[1]#ff0000:\"Critical below $CRIT[1] RPM\" ";
}
else */
if ($parts[2] == "Temperature")
{
	$upper = max(60, $CRIT[1] + 3);
	$opt[1] = "--vertical-label '$CRIT[1] Celsius' -l0 -u$upper --title \"$sensorname\" ";

	$def[1] = "DEF:temp=$RRDFILE[1]:$DS[1]:MAX ";
	$def[1] .= "AREA:temp#ffd040:\"temperature (max)\" ";
	$def[1] .= "LINE:temp#ff8000 ";
	$def[1] .= "HRULE:$CRIT[1]#ff0000:\"Critical at $CRIT[1] C\" ";
}

else {
   include("check_mk-local.php");
}
 

?>
