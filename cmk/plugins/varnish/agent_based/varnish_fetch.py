#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, Service

from .lib import check_varnish_stats, Params, Section


def discover_varnish_fetch(section: Section) -> DiscoveryResult:
    if all(
        key in section
        for key in [
            "fetch_1xx",
            "fetch_204",
            "fetch_304",
            "fetch_bad",
            "fetch_eof",
            "fetch_failed",
            "fetch_zero",
        ]
    ):
        yield Service()


def check_varnish_fetch(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "fetch_oldhttp",
            "fetch_head",
            "fetch_eof",
            "fetch_zero",
            "fetch_304",
            "fetch_length",
            "fetch_failed",
            "fetch_bad",
            "fetch_close",
            "fetch_1xx",
            "fetch_chunked",
            "fetch_204",
        ],
    )


check_plugin_varnish_fetch = CheckPlugin(
    name="varnish_fetch",
    service_name="Varnish Fetch",
    sections=["varnish"],
    discovery_function=discover_varnish_fetch,
    check_function=check_varnish_fetch,
    check_ruleset_name="varnish_fetch",
    check_default_parameters={},
)
