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

#
# Worker
#
$i=0;
$def[$i] = "";
$opt[$i]     = " --title 'Worker'";
$ds_name[$i] = "Workers";
$color = '#00ff00';
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'IdleWorkers') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::area    ("var".$KEY, $color ,rrd::cut($VAL['NAME'],12), 'STACK' );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.0lf");
    }
}
$color = '#ff0000';
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'BusyWorkers') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::area    ("var".$KEY, $color, rrd::cut($VAL['NAME'],12), 'STACK' );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.0lf");
    }
}

#
# Slots
#
$i++;
$def[$i] = "";
$opt[$i]     = " --title 'Slots'";
$ds_name[$i] = "Slots";
$color = '#ff0000';
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'TotalSlots') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::area    ("var".$KEY, $color,rrd::cut($VAL['NAME'],12) );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.0lf");
   }
}
$color = '#00ff00';
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'OpenSlots') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::area    ("var".$KEY, $color,rrd::cut($VAL['NAME'],12) );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.0lf");
   }
}

#
# Requests per Second 
#
$i++;
$def[$i]     = "";
$opt[$i]     = " --title Requests/sec";
$ds_name[$i] = "Requests/sec";
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
$opt[$i]     = " --title 'Bytes per Second'";
$ds_name[$i] = "Bytes/sec";
foreach ($this->DS as $KEY=>$VAL) {
    if($VAL['NAME'] == 'BytesPerSec') {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::line1   ("var".$KEY, rrd::color($KEY),rrd::cut($VAL['NAME'],16), 'STACK' );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.1lf %sb/s");
    }
}

#
# Stats 
#
$i++;
$def[$i]     = "";
$opt[$i]     = " --title 'Worker States'";
$ds_name[$i] = "Worker States";
foreach ($this->DS as $KEY=>$VAL) {
    if(preg_match('/^State_/', $VAL['NAME'])) {
        $def[$i]    .= rrd::def     ("var".$KEY, $VAL['RRDFILE'], $VAL['DS'], "AVERAGE");
        $def[$i]    .= rrd::line1   ("var".$KEY, rrd::color($KEY),rrd::cut($VAL['NAME'],16), 'STACK' );
        $def[$i]    .= rrd::gprint  ("var".$KEY, array("LAST","MAX","AVERAGE"), "%6.0lf".$VAL['UNIT']);
   }
}

?>
