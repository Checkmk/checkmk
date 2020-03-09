<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
