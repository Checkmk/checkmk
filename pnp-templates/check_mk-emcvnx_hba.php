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

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
}

$servicedesc = str_replace("_", " ", $servicedesc);

$opt[1] = "--vertical-label 'I/O (Blocks/s)' -X0  --title \"iSCSI traffic $hostname / $servicedesc\" ";

$def[1]  = 
           "HRULE:0#a0a0a0 ".
# read
           "DEF:read_blocks=$RRD[read_blocks] ".
           "AREA:read_blocks#40c080:\"Read \" ".
           "GPRINT:read_blocks:LAST:\"%8.1lf Blocks/s last\" ".
           "GPRINT:read_blocks:AVERAGE:\"%6.1lf Blocks/s avg\" ".
           "GPRINT:read_blocks:MAX:\"%6.1lf Blocks/s max\\n\" ";

# write
$def[1] .=
           "DEF:write_blocks=$RRD[write_blocks] ".
           "CDEF:write_blocks_neg=write_blocks,-1,* ".
           "AREA:write_blocks_neg#4080c0:\"Write  \"  ".
           "GPRINT:write_blocks:LAST:\"%6.1lf Blocks/s last\" ".
           "GPRINT:write_blocks:AVERAGE:\"%6.1lf Blocks/s avg\" ".
           "GPRINT:write_blocks:MAX:\"%6.1lf Blocks/s max\\n\" ".
           "";

?>

