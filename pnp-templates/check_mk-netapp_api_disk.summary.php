<?php
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

setlocale(LC_ALL, "POSIX");

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:AVERAGE";
}

$sizegb = sprintf("%.1f", $MAX[1]);

$opt[1] = "--vertical-label Bytes -l 0 -b 1024 --title 'Total raw capacity of $hostname' ";
# First graph show current filesystem usage
$def[1] = "DEF:bytes=$RRD[total_disk_capacity] ";
$def[1] .= "AREA:bytes#00ffc6:\"Capacity\" ";

# read ops
$opt[2] = "--vertical-label Disks -l 0 --title 'Spare and broken disks of $hostname' ";
$def[2] = "".
"DEF:sparedisks=$RRD[spare_disks] ".
"LINE:sparedisks#00e060:\" Spare  \" ".
"GPRINT:sparedisks:LAST:\"%7.0lf last\" ".
"GPRINT:sparedisks:AVERAGE:\"%7.0lf avg\" ".
"GPRINT:sparedisks:MAX:\"%7.0lf max\\n\" ".

"DEF:brokendisks=$RRD[failed_disks] ".
"LINE:brokendisks#e04000:\" Failed\" ".
"GPRINT:brokendisks:LAST:\"%7.0lf last\" ".
"GPRINT:brokendisks:AVERAGE:\"%7.0lf avg\" ".
"GPRINT:brokendisks:MAX:\"%7.0lf max\\n\" ";

?>
