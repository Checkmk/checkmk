#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MK_SAP_HANA_PLUGIN_PATH="${DIR}/../../../../agents/plugins/mk_sap_hana"

#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'

oneTimeSetUp () {

    export MK_CONFDIR=${SHUNIT_TMPDIR}
    export USERSTOREKEY="storekey"

    # shellcheck disable=SC1090
    . "$MK_SAP_HANA_PLUGIN_PATH" >/dev/null 2>&1

    # Mock sys calls
    nslookup () {
        if [ "$1" = "lavdb10y04001" ];then
            cat <<"output"
Server:		127.0.0.53
Address:	127.0.0.53#53

Non-authoritative answer:
Address: 192.168.1.1
output
        fi
    }
    ifconfig () {
        cat <<"output"
wlo1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
    inet 192.168.1.1
output
    }

}

#   .--tests---------------------------------------------------------------.
#   |                        _            _                                |
#   |                       | |_ ___  ___| |_ ___                          |
#   |                       | __/ _ \/ __| __/ __|                         |
#   |                       | ||  __/\__ \ |_\__ \                         |
#   |                        \__\___||___/\__|___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.

test_mk_sap_hana_single_hostname () {

    # Mock su / python call
    su () {

        if { [[ "$4"  == *"sid"* ]] && [[ "$2" == *"inst_user"* ]] && [[ "$4" == *"landscapeHostConfiguration.py"* ]]; }; then
        cat <<output
| Host |
|      |
|      |
| ------------- |
| lavdb10y04001 |
output
        fi
    }

    actual=$(sap_hana_internal_hostname "sid" "inst" "inst_user")
    expected="lavdb10y04001"
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_multiple_hostnames () {

    # Mock su / python call
    su () {

        if { [[ "$4"  == *"sid"* ]] && [[ "$2" == *"inst_user"* ]] && [[ "$4" == *"landscapeHostConfiguration.py"* ]]; }; then
        cat <<output
| Host |
|      |
|      |
| ------------- |
| lavdb10y04002 |
| lavdb10y04001 |
output
        fi
    }

    actual=$(sap_hana_internal_hostname "sid" "inst" "inst_user")
    expected="lavdb10y04001"
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_multiple_hostnames_non_active () {

    # Mock su / python call
    su () {

        if { [[ "$4"  == *"sid"* ]] && [[ "$2" == *"inst_user"* ]] && [[ "$4" == *"landscapeHostConfiguration.py"* ]]; }; then
        cat <<output
| Host |
|      |
|      |
| ------------- |
| non-active-host1 |
| non-active-host2 |
output
        fi
    }

    actual=$(sap_hana_internal_hostname "sid" "inst" "inst_user")
    expected=""
    assertEquals "$expected" "$actual"

}

# shellcheck disable=SC1090
. "${DIR}/../../../shunit2"
