<?php
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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


# Cut the relevant bits from the Nagios Service Description.
# This is a little complicated.
$item = substr($servicedesc, 14);
$item = str_replace("_Size", "",  $item);
$dbname = $item;


$opt[1]     = "--lower=0 --upper=".($CRIT[1]+10)." --vertical-label \"Bytes\" --title \"MySQL DB $dbname Size\" ";
# Paint nice gradient using MySQLs colours.
$def[1]     = rrd::def("var1", $RRDFILE[1], $DS[1], "MAX")
           . rrd::gradient('var1', '015a84', 'e97b00', 'Database Size', 50)
           . rrd::gprint("var1", array("LAST", "MAX", "AVERAGE"), "%6.2lf%sB")
           # paint a little line on top of it for visibility.
           . "LINE2:var1#e57900 ";

# Draw vertical line with the current warn/crit levels.
if (isset($WARN[1]) and $WARN[1] != "") {
    $def[1] .= "HRULE:$WARN[1]#FFFF00:\"\" ".
               "HRULE:$CRIT[1]#FF0000:\"\" ".
               "";
    }

?>
