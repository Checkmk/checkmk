#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    simple_levels,
)
from cmk.gui.valuespec import Dictionary, Integer


def _parameter_valuespec_mcafee_web_gateway_misc():
    return Dictionary(
        elements=[
            (
                "clients",
                simple_levels.SimpleLevels(
                    Integer,
                    title=_("Upper levels for clients"),
                    default_levels=(0, 0),
                    default_value=None,
                ),
            ),
            (
                "network_sockets",
                simple_levels.SimpleLevels(
                    Integer,
                    title=_("Upper levels for open network sockets"),
                    default_levels=(0, 0),
                    default_value=None,
                ),
            ),
            (
                "time_to_resolve_dns",
                simple_levels.SimpleLevels(
                    Integer,
                    title=_("Upper levels for time to resolve DNS"),
                    default_levels=(1500, 2000),
                    default_value=(1500, 2000),
                    unit=_("ms"),
                ),
            ),
            (
                "time_consumed_by_rule_engine",
                simple_levels.SimpleLevels(
                    Integer,
                    title=_("Upper levels for time consumed by rule engine"),
                    default_levels=(1500, 2000),
                    default_value=(1500, 2000),
                    unit=_("ms"),
                ),
            ),
            (
                "client_requests_http",
                Levels(
                    title=_("Upper levels for the number of http request per second"),
                    default_levels=(500.0, 1000.0),
                    default_value=(500.0, 1000.0),
                    default_difference=(10.0, 20.0),
                    unit="per second",
                ),
            ),
            (
                "client_requests_https",
                Levels(
                    title=_("Upper levels for the number of https request per second"),
                    default_levels=(500.0, 1000.0),
                    default_value=(500.0, 1000.0),
                    default_difference=(10.0, 20.0),
                    unit="per second",
                ),
            ),
            (
                "client_requests_httpv2",
                Levels(
                    title=_("Upper levels for the number of httpv2 request per second"),
                    default_levels=(500.0, 1000.0),
                    default_value=(500.0, 1000.0),
                    default_difference=(10.0, 20.0),
                    unit="per second",
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="mcafee_web_gateway_misc",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mcafee_web_gateway_misc,
        title=lambda: _("McAfee web gateway miscellaneous"),
    )
)
