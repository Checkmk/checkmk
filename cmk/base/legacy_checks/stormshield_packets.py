#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import get_rate, get_value_store, SNMPTree
from cmk.base.plugins.agent_based.utils.stormshield import DETECT_STORMSHIELD

# Unfortunalty we can not use the normal interface names here, because
# the interface IDs from the enterprise MIBs and RFC are not the same.
# We decided using the interface description for inventory (best practise)


def inventory_stormshield_packets(info):
    for descrip, _name, iftype, _pktaccepted, _pktblocked, _pkticmp, _tcp, _udp in info:
        if iftype.lower() in ["ethernet", "ipsec"]:
            yield descrip, {}


def check_stormshield_packets(item, _no_params, info):
    for descrip, name, _iftype, pktaccepted, pktblocked, pkticmp, tcp, udp in info:
        if item == descrip:
            now = time.time()
            rate_pktaccepted = get_rate(
                get_value_store(), "acc_%s" % item, now, int(pktaccepted), raise_overflow=True
            )
            rate_pktblocked = get_rate(
                get_value_store(), "block_%s" % item, now, int(pktblocked), raise_overflow=True
            )
            rate_pkticmp = get_rate(
                get_value_store(), "icmp_%s" % item, now, int(pkticmp), raise_overflow=True
            )
            infotext = "[%s], tcp: %s, udp: %s" % (name, tcp, udp)
            perfdata = [
                ("tcp_active_sessions", tcp),
                ("udp_active_sessions", udp),
                ("packages_accepted", rate_pktaccepted),
                ("packages_blocked", rate_pktblocked),
                ("packages_icmp_total", rate_pkticmp),
            ]
            yield 0, infotext, perfdata


check_info["stormshield_packets"] = LegacyCheckDefinition(
    detect=DETECT_STORMSHIELD,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11256.1.4.1.1",
        oids=["2", "3", "6", "11", "12", "16", "23", "24"],
    ),
    service_name="Packet Stats %s",
    discovery_function=inventory_stormshield_packets,
    check_function=check_stormshield_packets,
)
