#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Argumente
# 0 = heute
# -1 = gestern
# ...

set_times() {
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
    time_start=$((time_now - offset * 86400))
    if [[ $2 ]]; then
        length=$2
        time_end=$((time_start + length * 86400))
    else
        time_end=$(date +%s)
    fi

    export time_start time_end
}

run_query() {
    cat <<HERE | lq
GET log
Filter: class = 3
Filter: service_description > ""
Filter: time > $time_start
Filter: time < $time_end
Columns: host_name service_description plugin_output
HERE
}

set_times "$@"
run_query
