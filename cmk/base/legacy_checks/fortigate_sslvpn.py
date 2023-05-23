#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, discover, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fortinet import DETECT_FORTIGATE


def parse_fortigate_sslvpn(info):
    parsed = {}
    for domain_name, domain_info in zip(info[0], info[1]):
        parsed[domain_name[0]] = {
            "state": domain_info[0],
            "users": int(domain_info[1]),
            "web_sessions": int(domain_info[2]),
            "tunnels": int(domain_info[3]),
            "tunnels_max": int(domain_info[4]),
        }
    return parsed


def check_fortigate_sslvpn(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if params is None:
        params = {}

    fn_bool_state = {"1": "disabled", "2": "enabled"}
    yield 0, "%s" % fn_bool_state[data["state"]]

    yield check_levels(
        data["users"], "active_vpn_users", None, infoname="Users", human_readable_func=str
    )

    yield check_levels(
        data["web_sessions"],
        "active_vpn_websessions",
        None,
        infoname="Web sessions",
        human_readable_func=str,
    )

    yield check_levels(
        data["tunnels"],
        "active_vpn_tunnels",
        params.get("tunnel_levels"),
        infoname="Tunnels",
        boundaries=(0, data["tunnels_max"]),
        human_readable_func=str,
    )


check_info["fortigate_sslvpn"] = LegacyCheckDefinition(
    detect=DETECT_FORTIGATE,
    discovery_function=discover(),
    check_function=check_fortigate_sslvpn,
    parse_function=parse_fortigate_sslvpn,
    service_name="VPN SSL %s",
    check_ruleset_name="fortigate_sslvpn",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.3.2.1.1",
            oids=["2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12356.101.12.2.3.1",
            oids=["1", "2", "4", "6", "7"],
        ),
    ],
)
