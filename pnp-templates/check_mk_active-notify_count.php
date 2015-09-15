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

$title = str_replace("_", " ", $servicedesc);

$area_colors = array( "beff5f", "5fffef", "5faaff", "cc5fff", "ff5fe2", "ff5f6c", "ff975f", "ffec5f");
$line_colors = array( "5f7a2f", "2f8077", "2f5580", "662f80", "802f71", "802f36", "804b2f", "80762f");

$parts = explode(' ', $NAGIOS_CHECK_COMMAND);
$minutes = $parts[1];

$opt[1] = "--vertical-label 'Notifications' -l0 --title \"$title (in last $minutes min)\" ";
$def[1] = "";
$nr = 0;
foreach ($DS AS $i => $ds_val) {
    $contact_name = substr($NAME[$i], 0, strpos($NAME[$i], '_'));
    $varname = "notto$nr";
    $def[1] .=  "DEF:$varname=".$RRDFILE[$i].":$ds_val:MAX " ;

    $def[1] .= "LINE1:$varname#".$line_colors[$i % 8].":\"".sprintf("%-20s", $contact_name)."\" ";
    $def[1] .= "GPRINT:$varname:MAX:\"%3.lf\\n\" ";
    $nr += 1;
}

?>
