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
# read_ops=1.195013;;;;
# write_ops=2.257247;;;;
# net_data_recv=713.821034;;;;
# net_data_sent=2396.399187;;;;
# read_bytes=20819.780167;;;;
# write_bytes=832.791207;;;;

$opt[1] = "--vertical-label OPS --title \"Operations per second: $hostname / $servicedesc\" ";

$def[1] = "".
# read ops
"DEF:readops=$RRDFILE[1]:$DS[1]:MAX ".
"LINE:readops#00e060:\" Read OPS \" ".
"GPRINT:readops:LAST:\"%7.1lf OPS last\" ".
"GPRINT:readops:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:readops:MAX:\"%7.1lf OPS max\\n\" ".

# write ops
"DEF:writeops=$RRDFILE[2]:$DS[2]:MAX ".
"CDEF:minuswriteops=writeops,-1,* ".
"LINE:minuswriteops#0080e0:\"Write OPS \" ".
"GPRINT:writeops:LAST:\"%7.1lf OPS last\" ".
"GPRINT:writeops:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:writeops:MAX:\"%7.1lf OPS max\\n\" ".

"";

$opt[2] = "--vertical-label Bytes -b 1024 --title \"Net Data Traffic: $hostname / $servicedesc\" ";

$def[2] = "".
# net data recv
"DEF:data_recv=$RRDFILE[3]:$DS[3]:MAX ".
"LINE:data_recv#607030:\" Net Send \" ".
"GPRINT:data_recv:LAST:\"%7.1lf OPS last\" ".
"GPRINT:data_recv:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:data_recv:MAX:\"%7.1lf OPS max\\n\" ".

# net data send
"DEF:data_sent=$RRDFILE[4]:$DS[4]:MAX ".
"CDEF:minusdata_sent=data_sent,-1,* ".
"LINE:minusdata_sent#703090:\" Net Recv \" ".
"GPRINT:data_sent:LAST:\"%7.1lf OPS last\" ".
"GPRINT:data_sent:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:data_sent:MAX:\"%7.1lf OPS max\\n\" ".

"";

$opt[3] = "--vertical-label Bytes -b 1024 --title \"Bytes Traffic: $hostname / $servicedesc\" ";
$def[3] = "".
# read bytes
"DEF:read_bytes=$RRDFILE[5]:$DS[5]:MAX ".
"LINE:read_bytes#607030:\" Bytes Send \" ".
"GPRINT:read_bytes:LAST:\"%7.1lf OPS last\" ".
"GPRINT:read_bytes:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:read_bytes:MAX:\"%7.1lf OPS max\\n\" ".

# write bytes
"DEF:write_bytes=$RRDFILE[6]:$DS[6]:MAX ".
"CDEF:minuswrite_bytes=write_bytes,-1,* ".
"LINE:minuswrite_bytes#703090:\" Bytes Recv \" ".
"GPRINT:write_bytes:LAST:\"%7.1lf OPS last\" ".
"GPRINT:write_bytes:AVERAGE:\"%7.1lf OPS avg\" ".
"GPRINT:write_bytes:MAX:\"%7.1lf OPS max\\n\" ".
"";

?>
