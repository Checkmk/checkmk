#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_worker(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["n_wrk_failed", "n_wrk_queued"]):
        yield Service()


def check_varnish_worker(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "n_wrk_lqueue",
            "n_wrk_create",
            "n_wrk_drop",
            "n_wrk",
            "n_wrk_failed",
            "n_wrk_queued",
            "n_wrk_max",
        ],
    )


check_plugin_varnish_worker = CheckPlugin(
    name="varnish_worker",
    service_name="Varnish Worker",
    sections=["varnish"],
    discovery_function=discover_varnish_worker,
    check_function=check_varnish_worker,
    check_ruleset_name="varnish_worker",
    check_default_parameters={},
)
