#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_cache(section: Section) -> DiscoveryResult:
    if "cache_miss" in section:
        yield Service()


def check_varnish_cache(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "cache_miss",
            "cache_hit",
            "cache_hitpass",
        ],
    )


check_plugin_varnish_cache = CheckPlugin(
    name="varnish_cache",
    service_name="Varnish Cache",
    sections=["varnish"],
    discovery_function=discover_varnish_cache,
    check_function=check_varnish_cache,
    check_ruleset_name="varnish_cache",
    check_default_parameters={},
)
