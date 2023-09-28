#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api import v1
from cmk.base.plugins.agent_based.utils import mcafee_gateway


def discovery(section: mcafee_gateway.Section) -> v1.type_defs.DiscoveryResult:
    if section.time_consumed_by_rule_engine is not None:
        yield v1.Service()


def check(
    params: mcafee_gateway.MiscParams, section: mcafee_gateway.Section
) -> v1.type_defs.CheckResult:
    if section.time_consumed_by_rule_engine is not None:
        yield from v1.check_levels(
            value=section.time_consumed_by_rule_engine.total_seconds(),
            metric_name="time_consumed_by_rule_engine",
            levels_upper=mcafee_gateway._get_param_in_seconds(
                params["time_consumed_by_rule_engine"]
            ),
            render_func=v1.render.timespan,
        )


v1.register.check_plugin(
    name="mcafee_webgateway_time_consumed_by_rule_engine",
    sections=["mcafee_webgateway_misc"],
    service_name="Time consumed by rule engine",
    check_ruleset_name="mcafee_web_gateway_misc",
    check_function=check,
    discovery_function=discovery,
    check_default_parameters=mcafee_gateway.MISC_DEFAULT_PARAMS,
)
