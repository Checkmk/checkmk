#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckPlugin, CheckResult, DiscoveryResult, render, Service
from cmk.plugins.lib import mcafee_gateway


def discovery(section: mcafee_gateway.Section) -> DiscoveryResult:
    if section.time_to_resolve_dns is not None:
        yield Service()


def check(params: mcafee_gateway.MiscParams, section: mcafee_gateway.Section) -> CheckResult:
    if section.time_to_resolve_dns is not None:
        yield from check_levels_v1(
            value=section.time_to_resolve_dns.total_seconds(),
            metric_name="time_to_resolve_dns",
            levels_upper=mcafee_gateway.get_param_in_seconds(params["time_to_resolve_dns"]),
            render_func=render.timespan,
        )


check_plugin_mcafee_webgateway_time_to_resolve_dns = CheckPlugin(
    name="mcafee_webgateway_time_to_resolve_dns",
    service_name="Time to resolve DNS",
    check_ruleset_name="mcafee_web_gateway_misc",
    sections=["webgateway_misc"],
    check_function=check,
    discovery_function=discovery,
    check_default_parameters=mcafee_gateway.MISC_DEFAULT_PARAMS,
)
