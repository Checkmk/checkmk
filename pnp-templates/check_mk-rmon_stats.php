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

$opt[1] = "--vertical-label 'pkts/sec' -u 10 -X0 --title \"$servicedesc on $hostname\" ";

$stats = array(
  array(1,  "BCAST", "", "#777777", ""),
  array(2,  "MCAST", "  ", "#a00000", ""),
  array(3,  "0-63B", "  ", "#ff0000", ""),
  array(4,  "64-127B", "  ", "#ffc000", "\\n"),
  array(5,  "128-255B", " ", "#f000f0", ""),
  array(6,  "256-511B", "  ", "#00b0b0", ""),
  array(7,  "512-1024B", "   ", "#c060ff", ""),
  array(8,  "1024-1518B", "   ", "#00f040", "\\n")
);

$def[1] = "";

foreach ($stats as $entry) {
   list($i, $stat, $spaces, $color, $nl) = $entry;
   $def[1] .= "DEF:$stat=$RRDFILE[$i]:$DS[$i]:MAX ";
   $def[1] .= "AREA:$stat$color:\"$stat\":STACK ";
   $def[1] .= "GPRINT:$stat:LAST:\"$spaces%3.0lf$nl\" ";
}

