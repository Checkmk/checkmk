#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import time

from cmk.base.check_api import check_levels, get_rate, LegacyCheckDefinition
from cmk.base.check_legacy_includes.f5_bigip import DETECT, get_conn_rate_params
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["f5_bigip_conns_default_levels"] = {
    "conns": (25000, 30000),
    "ssl_conns": (25000, 30000),
    "http_req_rate": (500, 1000),
}


def inventory_f5_bigip_conns(info):
    if info:
        return [(None, {})]
    return []


def check_f5_bigip_conns(item, params, info):  # pylint: disable=too-many-branches
    # Connection rate
    now = time.time()
    total_native_compat_rate = 0.0
    conns_dict = {}

    for line in info:
        if line[2] != "":
            native_conn_rate = get_rate("native", now, int(line[2]))
        else:
            native_conn_rate = 0

        if line[3] != "":
            compat_conn_rate = get_rate("compat", now, int(line[3]))
        else:
            compat_conn_rate = 0

            total_native_compat_rate += native_conn_rate + compat_conn_rate

        if line[4] != "":
            stat_http_req_rate = get_rate("stathttpreqs", now, int(line[4]))
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


check_info["f5_bigip_conns"] = LegacyCheckDefinition(
    detect=DETECT,
    check_function=check_f5_bigip_conns,
    discovery_function=inventory_f5_bigip_conns,
    service_name="Open Connections",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1.1.2",
        oids=["1.8", "9.2", "9.6", "9.9", "1.56"],
    ),
    check_ruleset_name="f5_connections",
    default_levels_variable="f5_bigip_conns_default_levels",
)
