#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.utils.hostaddress import HostName

from cmk.base.check_api import host_name, is_ipv6_primary
from cmk.base.config import active_check_info


def check_traceroute_arguments(params: Mapping[str, Any]) -> list[str]:
    args = ["$HOSTADDRESS$"]

    if params["dns"]:
        args.append("--use_dns")

    return [
        *args,
        f"--probe_method={params['method'] or 'udp'}",
        f"--ip_address_family={params['address_family'] or ('ipv6' if is_ipv6_primary(HostName(host_name())) else 'ipv4')}",
        "--routers_missing_warn",
        *(router for router, state in params["routers"] if state == "W"),
        "--routers_missing_crit",
        *(router for router, state in params["routers"] if state == "C"),
        "--routers_found_warn",
        *(router for router, state in params["routers"] if state == "w"),
        "--routers_found_crit",
        *(router for router, state in params["routers"] if state == "c"),
    ]


active_check_info["traceroute"] = {
    "command_line": "check_traceroute $ARG1$",
    "argument_function": check_traceroute_arguments,
    "service_description": lambda params: "Routing",
}
