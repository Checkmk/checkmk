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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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
