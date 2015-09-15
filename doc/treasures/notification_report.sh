#!/bin/bash
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
