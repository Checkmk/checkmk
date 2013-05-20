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

# Copied most parts from the pnp template check_apachestatus_auto.php.

// Make data sources available via names
$RRD = array();
foreach ($NAME as $i => $n) {
    $RRD[$n] = "$RRDFILE[$i]:$DS[$i]:MAX";
    $WARN[$n] = $WARN[$i];
    $CRIT[$n] = $CRIT[$i];
    $MIN[$n]  = $MIN[$i];
    $MAX[$n]  = $MAX[$i];
    $ACT[$n]  = $ACT[$i];
}

$i=0;
$def[$i]  = "";
$opt[$i]  = " --title '$hostname: $servicedesc Connections' -l 0";

$def[$i] .= "DEF:varTotal=${RRD['TotalSlots']} "; 
$def[$i] .= "DEF:varOpen=${RRD['OpenSlots']} "; 
$def[$i] .= "HRULE:${ACT['TotalSlots']}#000000:\"Total Slots ${ACT['TotalSlots']}\" ";

if ($WARN['OpenSlots'] != 0) {
    $warn_used= $ACT['TotalSlots'] - $WARN['OpenSlots'];
    $def[$i] .= "HRULE:$warn_used#FF8B00:\"Warn Used Slots $warn_used\" ";
}
if ($CRIT['OpenSlots'] != 0) {
    $crit_used= $ACT['TotalSlots'] - $CRIT['OpenSlots'];
    $def[$i] .= "HRULE:$crit_used#DC3609:\"Crit Used Slots $crit_used\" ";
}
$def[$i] .= "COMMENT:\"\\n\" ";


$def[$i] .= "CDEF:usedslots=varTotal,varOpen,- ";
$def[$i] .= "GPRINT:usedslots:LAST:\"Used Slots          Last %5.1lf\" ";
$def[$i] .= "GPRINT:usedslots:MAX:\"Max %5.1lf\" ";
$def[$i] .= "GPRINT:usedslots:AVERAGE:\"Average %5.1lf\" ";
$def[$i] .= "COMMENT:\"\\n\" ";

foreach ($this->DS as $KEY=>$VAL) {
    if(preg_match('/^State_/', $VAL['NAME'])) {
        $def[$i] .= "DEF:var${KEY}=${VAL['RRDFILE']}:${DS[$VAL['DS']]}:AVERAGE "; 
        $def[$i] .= "AREA:var${KEY}".rrd::color($KEY).":\"".rrd::cut(substr($VAL['NAME'],6),16) ."\":STACK ";
        $def[$i] .= "GPRINT:var${KEY}:LAST:\"Last %5.1lf\" ";
        $def[$i] .= "GPRINT:var${KEY}:MAX:\"Max %5.1lf\" ";
        $def[$i] .= "GPRINT:var${KEY}:AVERAGE:\"Average %5.1lf\" ";
        $def[$i] .= "COMMENT:\"\\n\" ";
   }
}

#
# Requests per Second 
#
$i++;
$def[$i]     = "";
$opt[$i]     = " --title '$hostname: $servicedesc Requests/sec' ";
$color = '#000000';
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'ReqPerSec') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::line1   ("var".$KEY, $color, rrd::cut($VAL['NAME'],16), 'STACK' );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.1lf/s");
    }
}
#
# Bytes per Second 
#
$i++;
$def[$i]     = "";
$opt[$i]     = " --title '$hostname: $servicedesc Bytes per Second'";
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'BytesPerSec') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::line1   ("var".$KEY, rrd::color($KEY),rrd::cut($VAL['NAME'],16), 'STACK' );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.1lf %sb/s");
    }
}
?>
