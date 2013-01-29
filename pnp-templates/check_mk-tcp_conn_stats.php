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

$opt[1] = "--vertical-label 'Number' -u 10 -X0 --title \"TCP Connection stats on $hostname\" ";

$stats = array(
  array(2,  "SYN_SENT", "   ", "#a00000", ""),
  array(3,  "SYN_RECV", "   ", "#ff4000", ""),
  array(1,  "ESTABLISHED", "", "#00f040", ""),
  array(6,  "TIME_WAIT", "  ", "#00b0b0", "\\n"),
  array(4,  "LAST_ACK", "   ", "#c060ff", ""),
  array(5,  "CLOSE_WAIT", " ", "#f000f0", ""),
  array(7,  "CLOSED", "     ", "#ffc000", ""),
  array(8,  "CLOSING", "    ", "#ffc080", "\\n"),
  array(9,  "FIN_WAIT1", "  ", "#cccccc", ""),
  array(10, "FIN_WAIT2", "  ", "#888888", "\\n")
);

$def[1] = "";

foreach ($stats as $entry) {
   list($i, $stat, $spaces, $color, $nl) = $entry;
   $def[1] .= "DEF:$stat=$RRDFILE[$i]:$DS[$i]:MAX ";
   $def[1] .= "AREA:$stat$color:\"$stat\":STACK ";
   $def[1] .= "GPRINT:$stat:LAST:\"$spaces%3.0lf$nl\" ";
}

