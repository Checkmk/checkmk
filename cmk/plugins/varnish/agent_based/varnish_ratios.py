#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, render, Service

from .lib import check_varnish_ratio, Params, Section


def discover_varnish_cache_hit_ratio(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["cache_miss", "cache_hit"]):
        yield Service()


def check_varnish_cache_hit_ratio(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_ratio(params, section, ("cache_hit", "cache_miss", "cache_hit_ratio"))


check_plugin_varnish_cache_hit_ratio = CheckPlugin(
    name="varnish_cache_hit_ratio",
    service_name="Varnish Cache Hit Ratio",
    sections=["varnish"],
    discovery_function=discover_varnish_cache_hit_ratio,
    check_function=check_varnish_cache_hit_ratio,
    check_ruleset_name="varnish_cache_hit_ratio",
    check_default_parameters={"levels_lower": (70.0, 60.0)},
)


def discover_varnish_backend_success_ratio(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["backend_fail", "backend_conn"]):
        yield Service()


def check_varnish_backend_success_ratio(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_ratio(
        params, section, ("backend_conn", "backend_fail", "varnish_backend_success_ratio")
    )


check_plugin_varnish_backend_success_ratio = CheckPlugin(
    name="varnish_backend_success_ratio",
    service_name="Varnish Backend Success Ratio",
    sections=["varnish"],
    discovery_function=discover_varnish_backend_success_ratio,
    check_function=check_varnish_backend_success_ratio,
    check_ruleset_name="varnish_backend_success_ratio",
    check_default_parameters={"levels_lower": (70.0, 60.0)},
)


def check_varnish_worker_thread_ratio(params: Params, section: Section) -> CheckResult:
    worker_create = section["n_wrk_create"].value
    warn, crit = params["levels_lower"]
    yield from check_levels(
        100.0 * section["n_wrk"].value / worker_create if worker_create > 0 else 0.0,
        "varnish_worker_thread_ratio",
        (None, None, warn, crit),
        human_readable_func=render.percent,
    )


def discover_varnish_worker_thread_ratio(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["n_wrk", "n_wrk_create"]):
        yield Service()


check_plugin_varnish_worker_thread_ratio = CheckPlugin(
    name="varnish_worker_thread_ratio",
    service_name="Varnish Worker Thread Ratio",
    sections=["varnish"],
    discovery_function=discover_varnish_worker_thread_ratio,
    check_function=check_varnish_worker_thread_ratio,
    check_ruleset_name="varnish_worker_thread_ratio",
    check_default_parameters={"levels_lower": (70.0, 60.0)},
)
