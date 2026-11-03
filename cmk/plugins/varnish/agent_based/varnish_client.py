#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_client(section: Section) -> DiscoveryResult:
    if "client_req" in section:
        yield Service()


def check_varnish_client(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "client_drop",
            "client_req",
            "client_conn",
            "client_drop_late",
        ],
    )


check_plugin_varnish_client = CheckPlugin(
    name="varnish_client",
    service_name="Varnish Client",
    sections=["varnish"],
    discovery_function=discover_varnish_client,
    check_function=check_varnish_client,
    check_ruleset_name="varnish_client",
    check_default_parameters={},
)
