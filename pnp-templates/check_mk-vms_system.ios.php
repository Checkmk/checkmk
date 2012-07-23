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

$opt[1] = "--vertical-label 'IOs per second' -l0 --title \"IOs on $hostname\" ";
$def[1] = ""
          . "DEF:direct=$RRDFILE[1]:$DS[1]:MAX "
          . "AREA:direct#38808f:\"Direct IOs/sec  \" "
          . "GPRINT:direct:LAST:\"last\: %8.0lf/s\" "
          . "GPRINT:direct:AVERAGE:\"avg\: %8.0lf/s\" "
          . "GPRINT:direct:MAX:\"max\: %8.0lf/s\\n\" "

          . "DEF:buffered=$RRDFILE[2]:$DS[2]:MAX "
          . "AREA:buffered#38b0cf:\"Buffered IOs/sec\":STACK "
          . "GPRINT:buffered:LAST:\"last\: %8.0lf/s\" "
          . "GPRINT:buffered:AVERAGE:\"avg\: %8.0lf/s\" "
          . "GPRINT:buffered:MAX:\"max\: %8.0lf/s\\n\" "
          ;
?>
