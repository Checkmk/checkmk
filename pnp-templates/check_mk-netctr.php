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

$nic_types = explode(".", $servicedesc);
$nic = substr($nic_types[0], 4);
$types = explode("_", $nic_types[1]);
$dir = $types[0];
$type = $types[1];

if ($dir == "rx")
  $dir = "IN";
else
  $dir = "OUT";

if ($type == "bytes") {
  $unit = "MByte/s";
  $div = 1024.0 * 1024.0;
  $color = "ffc000";
  $title = "Network throuput";
  $upperlimit = "--upper-limit 100.0";
}
else if ($type == "packets") {
  $unit = "Packets/s";
  $color = "c09000";
  $div = 1;
  $title = "Packets per second";
}
else {
  $unit = "per sec.";
  $div = 1;
  $color = "ff0000";
  if ($type == "errors")
    $title = "Errors";
  else if ($type == "collisions")
    $title = "Collisions";
  else
    $title = $type;

}

$opt[1] = "--vertical-label '$unit' -l0 $upperlimit --title \"$title $hostname / $nic ($dir)\" ";
#
#
#
$def[1]  = "DEF:val=$RRDFILE[1]:$DS[1]:MAX " ;
$def[1] .= "CDEF:mb=val,$div,/ " ;
$def[1] .= "AREA:mb#$color " ;
$def[1] .= "LINE:mb#a40 " ;
$def[1] .= "GPRINT:mb:LAST:\"%6.1lf $unit last\" " ;
$def[1] .= "GPRINT:mb:AVERAGE:\"%6.1lf $unit avg\" " ;
$def[1] .= "GPRINT:mb:MAX:\"%6.1lf $unit max\\n\" ";
?>
