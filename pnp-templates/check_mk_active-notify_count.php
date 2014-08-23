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

$title = str_replace("_", " ", $servicedesc);

$area_colors = array( "beff5f", "5fffef", "5faaff", "cc5fff", "ff5fe2", "ff5f6c", "ff975f", "ffec5f");
$line_colors = array( "5f7a2f", "2f8077", "2f5580", "662f80", "802f71", "802f36", "804b2f", "80762f");

$parts = explode(' ', $NAGIOS_CHECK_COMMAND);
$minutes = $parts[1];

$opt[1] = "--vertical-label 'Notifications' -l0 --title \"$title (in last $minutes min)\" ";
$def[1] = "";
foreach ($DS AS $i => $ds_val) {
    $contact_name = substr($NAME[$i], 0, strpos($NAME[$i], '_'));
    $def[1] .=  "DEF:$contact_name=".$RRDFILE[$i].":$ds_val:MAX " ;

    $def[1] .= "LINE1:$contact_name#".$line_colors[$i % 8].":\"".sprintf("%-20s", $contact_name)."\" ";
    $def[1] .= "GPRINT:$contact_name:MAX:\"%3.lf\\n\" ";
}

?>
