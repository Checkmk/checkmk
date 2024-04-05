#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""
from cmk.base.plugins.agent_based.agent_based_api import v1

from cmk.plugins.lib import mcafee_gateway


def discovery_webgateway_misc(
    section: mcafee_gateway.Section,
) -> v1.type_defs.DiscoveryResult:
    yield v1.Service()


def check_webgateway_misc(
    params: mcafee_gateway.MiscParams, section: mcafee_gateway.Section
) -> v1.type_defs.CheckResult:
    if section.client_count is not None:
        yield from v1.check_levels(
            section.client_count,
            levels_upper=params.get("clients"),
            metric_name="connections",
            label="Clients",
            render_func=str,
        )
    if section.socket_count is not None:
        yield from v1.check_levels(
            section.socket_count,
            levels_upper=params.get("network_sockets"),
            metric_name="open_network_sockets",
            label="Open network sockets",
            render_func=str,
        )


v1.register.check_plugin(
    name="mcafee_webgateway_misc",
    sections=["webgateway_misc"],
    service_name="Web gateway miscellaneous",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_function=check_webgateway_misc,
    discovery_function=discovery_webgateway_misc,
    check_default_parameters=mcafee_gateway.MISC_DEFAULT_PARAMS,
)
