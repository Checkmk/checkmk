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

