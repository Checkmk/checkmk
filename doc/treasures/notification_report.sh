#!/bin/bash
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

# Argumente
# 0 = heute
# -1 = gestern
# ...


set_times()
{
if [ $# -lt 1 ]; then
    echo "please add arguments"
    echo "     start_date, i.e. 0 for today 7am, 1 for yesterday 7am"
    echo "optional:     length, i.e. 5 for five days"
    echo "              if not specified, give full list till now"
    exit 1
fi

offset=$1

# Rechnen ab beginn des aktuellen tages (07 Uhr)
time_now=$(date -u +%s -d "today 0700")
time_start=$(( $time_now - $offset * 86400 ))
if [[ $2 ]]; then
    length=$2
    time_end=$(( $time_start + $length * 86400 ))
else
    time_end=$( date +%s )
fi

export time_start time_end
}


run_query()
{
echo "GET log 
Filter: class = 3
Filter: service_description > ""
Filter: time > $time_start
Filter: time < $time_end
Columns: host_name service_description plugin_output" | lq
}



set_times $@
run_query
