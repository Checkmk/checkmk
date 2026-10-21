#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_esi(section: Section) -> DiscoveryResult:
    if "esi_errors" in section:
        yield Service()


def check_varnish_esi(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "esi_errors",
            "esi_warnings",
        ],
    )


check_plugin_varnish_esi = CheckPlugin(
    name="varnish_esi",
    service_name="Varnish ESI",
    sections=["varnish"],
    discovery_function=discover_varnish_esi,
    check_function=check_varnish_esi,
    check_ruleset_name="varnish_esi",
    check_default_parameters={"errors": ("fixed", (1.0, 2.0))},
)
