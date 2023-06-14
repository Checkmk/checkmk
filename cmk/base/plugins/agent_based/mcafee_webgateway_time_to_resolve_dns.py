#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils import mcafee_gateway


def discovery(section: mcafee_gateway.Section) -> v1.type_defs.DiscoveryResult:
    if section.time_to_resolve_dns is not None:
        yield v1.Service()


def check(
    params: mcafee_gateway.MiscParams, section: mcafee_gateway.Section
) -> v1.type_defs.CheckResult:
    if section.time_to_resolve_dns is not None:
        yield from v1.check_levels(
            value=section.time_to_resolve_dns.total_seconds(),
            metric_name="time_to_resolve_dns",
            levels_upper=mcafee_gateway._get_param_in_seconds(params["time_to_resolve_dns"]),
            render_func=v1.render.timespan,
        )


v1.register.check_plugin(
    name="mcafee_webgateway_time_to_resolve_dns",
    service_name="Time to resolve DNS",
    check_ruleset_name="mcafee_web_gateway_misc",
    sections=["mcafee_webgateway_misc"],
    check_function=check,
    discovery_function=discovery,
    check_default_parameters=mcafee_gateway.MISC_DEFAULT_PARAMS,
)
