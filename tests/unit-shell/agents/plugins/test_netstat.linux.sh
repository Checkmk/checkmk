#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MK_NETSTAT_PLUGIN_PATH="${UNIT_SH_PLUGINS_DIR}/netstat.linux"

netstat() {
    echo '
Active Internet connections (servers and established)
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 127.0.0.1:5001          0.0.0.0:*               LISTEN
tcp        0      0 10.1.1.2:59482          52.41.171.126:443       ESTABLISHED
tcp        0      0 127.0.0.1:6556          127.0.0.1:60472         TIME_WAIT
tcp        0      0 127.0.0.1:57170         127.0.0.1:8086          ESTABLISHED
tcp        1      0 10.1.1.2:46376          10.3.1.99:631           CLOSE_WAIT
tcp6       0      0 :::6556                 :::*                    LISTEN
udp        0      0 127.0.0.53:53           0.0.0.0:*
udp        0      0 127.0.0.1:49341         127.0.0.1:49341         ESTABLISHED
udp6       0      0 :::5353                 :::*'
}

test_netstat_plugin() {
    #    alias netstat='_sample_netstat'
    response=$(. "$MK_NETSTAT_PLUGIN_PATH")
    assertEquals "convert LISTEN to LISTENING" "<<<netstat>>>
tcp        0      0 127.0.0.1:5001          0.0.0.0:*               LISTENING
tcp        0      0 10.1.1.2:59482          52.41.171.126:443       ESTABLISHED
tcp        0      0 127.0.0.1:6556          127.0.0.1:60472         TIME_WAIT
tcp        0      0 127.0.0.1:57170         127.0.0.1:8086          ESTABLISHED
tcp        1      0 10.1.1.2:46376          10.3.1.99:631           CLOSE_WAIT
tcp6       0      0 :::6556                 :::*                    LISTENING
udp        0      0 127.0.0.53:53           0.0.0.0:*
udp        0      0 127.0.0.1:49341         127.0.0.1:49341         ESTABLISHED
udp6       0      0 :::5353                 :::*" "$response"

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
