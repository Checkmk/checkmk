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

# Performance data from check:
# read_ops=0;;;;
# write_ops=0;;;;

$opt[1] = "--vertical-label OPS --title \"Operations per second: $hostname / $servicedesc\" ";

$def[1] = "".
# read ops
"DEF:readops=$RRDFILE[1]:$DS[1]:MAX ".
"AREA:readops#00e060:\" Read  \" ".
"GPRINT:readops:LAST:\"%7.1lf OPS last\" ".
"GPRINT:readops:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:readops:MAX:\"%7.1lf OPS max\\n\" ".

# write ops
"DEF:writeops=$RRDFILE[2]:$DS[2]:MAX ".
"CDEF:minuswriteops=writeops,-1,* ".
"AREA:minuswriteops#0080e0:\"Write  \" ".
"GPRINT:writeops:LAST:\"%7.1lf OPS last\" ".
"GPRINT:writeops:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:writeops:MAX:\"%7.1lf OPS max\\n\" ".

"";

?>
