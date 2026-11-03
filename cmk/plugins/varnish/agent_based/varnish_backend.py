#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_backend(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["backend_fail", "backend_unhealthy", "backend_busy"]):
        yield Service()


def check_varnish_backend(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "backend_busy",
            "backend_unhealthy",
            "backend_req",
            "backend_recycle",
            "backend_retry",
            "backend_fail",
            "backend_toolate",
            "backend_conn",
            "backend_reuse",
        ],
    )


check_plugin_varnish_backend = CheckPlugin(
    name="varnish_backend",
    service_name="Varnish Backend",
    sections=["varnish"],
    discovery_function=discover_varnish_backend,
    check_function=check_varnish_backend,
    check_ruleset_name="varnish_backend",
    check_default_parameters={},
)
