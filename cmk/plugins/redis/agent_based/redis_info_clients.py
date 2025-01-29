#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import check_levels, CheckPlugin, CheckResult, DiscoveryResult, Service
from cmk.plugins.redis.agent_based.redis_base import Section

# .
#   .--Clients-------------------------------------------------------------.
#   |                     ____ _ _            _                            |
#   |                    / ___| (_) ___ _ __ | |_ ___                      |
#   |                   | |   | | |/ _ \ '_ \| __/ __|                     |
#   |                   | |___| | |  __/ | | | |_\__ \                     |
#   |                    \____|_|_|\___|_| |_|\__|___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

# ...
# Clients
# connected_clients:1
# client_longest_output_list:0
# client_biggest_input_buf:0
# blocked_clients:0

# Description of possible output:
# connected_clients - Number of client connections (excluding connections from replicas)
# client_longest_output_list - longest output list among current client connections
# client_biggest_input_buf - biggest input buffer among current client connections
# blocked_clients - Number of clients pending on a blocking call (BLPOP, BRPOP, BRPOPLPUSH)


def discover_redis_info_clients(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item, data in section.items() if "Clients" in data)


def check_redis_info_clients(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    clients_data = section.get(item, {}).get("Clients")
    if not clients_data or clients_data is None:
        return

    for data_key, param_key, infotext in [
        ("connected_clients", "connected", "Number of client connections"),
        ("client_longest_output_list", "output", "Longest output list"),
        ("client_biggest_input_buf", "input", "Biggest input buffer"),
        ("blocked_clients", "blocked", "Number of clients pending on a blocking call"),
    ]:
        clients_value = clients_data.get(data_key)
        if clients_value is None:
            continue

        yield from check_levels(
            int(clients_value),
            metric_name="clients_%s" % param_key,
            levels_upper=params.get("%s_upper" % param_key),
            levels_lower=params.get("%s_lower" % param_key),
            render_func=lambda x: str(int(x)),
            label=infotext,
        )


check_plugin_redis_info_clients = CheckPlugin(
    name="redis_info_clients",
    service_name="Redis %s Clients",
    sections=["redis_info"],
    discovery_function=discover_redis_info_clients,
    check_function=check_redis_info_clients,
    check_ruleset_name="redis_info_clients",
    check_default_parameters={
        f"{param_key}_{direction}": ("no_levels", None)
        for param_key in ["connected", "output", "input", "blocked"]
        for direction in ["upper", "lower"]
    },
)
