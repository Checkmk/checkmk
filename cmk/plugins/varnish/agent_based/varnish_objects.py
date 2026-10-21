#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_objects(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["n_expired", "n_lru_nuked"]):
        yield Service()


def check_varnish_objects(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "n_expired",
            "n_lru_nuked",
            "n_lru_moved",
        ],
    )


check_plugin_varnish_objects = CheckPlugin(
    name="varnish_objects",
    service_name="Varnish Objects",
    sections=["varnish"],
    discovery_function=discover_varnish_objects,
    check_function=check_varnish_objects,
    check_ruleset_name="varnish_objects",
    check_default_parameters={},
)
