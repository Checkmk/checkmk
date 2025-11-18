#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MK_NETSTAT_PLUGIN_PATH="${UNIT_SH_PLUGINS_DIR}/netstat.linux"

ss() {
    echo '
Netid State      Recv-Q Send-Q            Local Address:Port        Peer Address:Port Process
tcp   LISTEN     0      4096                    0.0.0.0:2345             0.0.0.0:*'
}

test_netstat_plugin() {
    #    alias netstat='_sample_netstat'
    # shellcheck source=agents/plugins/netstat.linux
    response=$(. "$MK_NETSTAT_PLUGIN_PATH")
    assertEquals "convert LISTEN to LISTENING" "<<<netstat>>>
tcp   LISTENING     0      4096                    0.0.0.0:2345             0.0.0.0:*" "$response"

}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
