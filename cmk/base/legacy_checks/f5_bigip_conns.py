#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"


# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, SNMPTree, StringTable
from cmk.base.check_legacy_includes.f5_bigip import get_conn_rate_params
from cmk.plugins.f5_bigip.lib import F5_BIGIP

check_info = {}


def discover_f5_bigip_conns(info):
    if info:
        return [(None, {})]
    return []


def check_f5_bigip_conns(item, params, info):
    # Connection rate
    now = time.time()
    value_store = get_value_store()
    total_native_compat_rate = 0.0
    conns_dict = {}

    for line in info:
        if line[2] != "":
            native_conn_rate = get_rate(
                value_store, "native", now, int(line[2]), raise_overflow=True
            )
        else:
            native_conn_rate = 0

        if line[3] != "":
            compat_conn_rate = get_rate(
                value_store, "compat", now, int(line[3]), raise_overflow=True
            )
        else:
            compat_conn_rate = 0

        total_native_compat_rate += native_conn_rate + compat_conn_rate

        if line[4] != "":
            stat_http_req_rate = get_rate(
                value_store, "stathttpreqs", now, int(line[4]), raise_overflow=True
            )
        else:
            stat_http_req_rate = None

        if line[0] != "":
            conns_dict.setdefault("total", 0)
            conns_dict["total"] += int(line[0])

        if line[1] != "":
            conns_dict.setdefault("total_ssl", 0)
            conns_dict["total_ssl"] += int(line[1])

    try:
        conn_rate_params = get_conn_rate_params(params)
    except ValueError as err:
        yield 3, str(err)
        return

    # Current connections
    for val, params_values, perfkey, title in [
        (conns_dict.get("total"), params.get("conns"), "connections", "Connections"),
        (
            conns_dict.get("total_ssl"),
            params.get("ssl_conns"),
            "connections_ssl",
            "SSL connections",
        ),
        (total_native_compat_rate, conn_rate_params, "connections_rate", "Connections/s"),
        (stat_http_req_rate, params.get("http_req_rate"), "requests_per_second", "HTTP requests/s"),
    ]:
        # SSL may not be configured, eg. on test servers
        if val is None:
            yield 0, "%s: not configured" % title
        else:
            yield check_levels(val, perfkey, params_values, infoname=title)


def parse_f5_bigip_conns(string_table: StringTable) -> StringTable:
    return string_table


check_info["f5_bigip_conns"] = LegacyCheckDefinition(
    name="f5_bigip_conns",
    parse_function=parse_f5_bigip_conns,
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.1.2",
        oids=["1.8", "9.2", "9.6", "9.9", "1.56"],
    ),
    service_name="Open Connections",
    discovery_function=discover_f5_bigip_conns,
    check_function=check_f5_bigip_conns,
    check_ruleset_name="f5_connections",
    check_default_parameters={
        "conns": (25000, 30000),
        "ssl_conns": (25000, 30000),
        "http_req_rate": (500, 1000),
    },
)
