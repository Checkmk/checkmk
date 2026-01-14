#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, render, StringTable

check_info = {}

# Example output from agent:
# <<<openvpn_clients:sep(44)>>>
# wilhelmshilfe-hups1,84.161.206.33:58371,11267978,8134524,Sun Mar 10 14:02:27 2013
# wilhelmshilfe-hups365,84.161.206.33:59737,924198,809268,Sun Mar 10 13:59:14 2013
# wilhelmshilfe-bartenbach-redu,78.43.52.102:40411,492987861,516066364,Sun Mar 10 03:55:01 2013
# wilhelmshilfe-hups3,84.161.206.33:58512,8224815,6189879,Sun Mar 10 11:32:40 2013
# wilhelmshilfe-heiningen,46.5.209.251:3412,461581486,496901007,Fri Mar  8 10:02:38 2013
# wilhelmshilfe-hups5,84.161.206.33:60319,721646,336190,Sun Mar 10 14:23:30 2013
# wilhelmshilfe-suessen,92.198.38.212:3077,857194558,646128778,Fri Mar  8 10:02:38 2013
# wilhelmshilfe-hups6,84.161.206.33:61410,3204103,2793366,Sun Mar 10 11:59:13 2013
# wilhelmshilfe-gw-fau1,217.92.99.180:55683,109253134,96735180,Sun Mar 10 10:11:44 2013
# wilhelmshilfe-bendig,78.47.146.190:34475,5787319,19395097,Sat Mar  9 10:02:52 2013
# wilhelmshilfe-ursenwang,46.223.206.6:47299,747919254,922426625,Fri Mar  8 10:02:38 2013
# vpn-wilhelmshilfe.access.lihas.de,79.204.249.30:59046,12596972,31933023,Sun Mar 10 09:32:22 2013
# wilhelmshilfe-karlshof,92.198.38.214:3078,810996228,716994592,Fri Mar  8 10:02:39 2013


def discover_openvpn_clients(info):
    return [(l[0], None) for l in info]


def check_openvpn_clients(item, _no_params, info):
    for line in info:
        if line[0] == item:
            infos = ["Channel is up"]
            perfdata = []
            _name, _address, inbytes, outbytes, _date = line
            this_time = time.time()
            for what, val in [("in", int(inbytes)), ("out", int(outbytes))]:
                countername = f"openvpn_clients.{item}.{what}"
                bytes_per_sec = get_rate(
                    get_value_store(), countername, this_time, val, raise_overflow=True
                )
                infos.append(f"{what}: {render.iobandwidth(bytes_per_sec)}")
                perfdata.append((what, bytes_per_sec))
            return 0, ", ".join(infos), perfdata

    return 3, "Client connection not found"


def parse_openvpn_clients(string_table: StringTable) -> StringTable:
    return string_table


check_info["openvpn_clients"] = LegacyCheckDefinition(
    name="openvpn_clients",
    parse_function=parse_openvpn_clients,
    service_name="OpenVPN Client %s",
    discovery_function=discover_openvpn_clients,
    check_function=check_openvpn_clients,
)
