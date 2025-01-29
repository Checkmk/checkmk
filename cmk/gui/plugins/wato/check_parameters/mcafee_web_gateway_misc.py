#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The McAfee Web Gateway has been rebranded to Skyhigh Secure Web Gateway with its release 12.2.2.
Where possibile the "McAfee" string has been removed in favor of more generic therms.
The old plug-in names, value_store dict keys, and ruleset names have been kept for compatibility/history-keeping reasons.
"""

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer


def _parameter_valuespec_mcafee_web_gateway_misc():
    return Dictionary(
        elements=[
            (
                "clients",
                SimpleLevels(
                    Integer,
                    title=_("Upper levels for clients"),
                    default_levels=(0, 0),
                    default_value=None,
                ),
            ),
            (
                "network_sockets",
                SimpleLevels(
                    Integer,
                    title=_("Upper levels for open network sockets"),
                    default_levels=(0, 0),
                    default_value=None,
                ),
            ),
            (
                "time_to_resolve_dns",
                SimpleLevels(
                    Integer,
                    title=_("Upper levels for time to resolve DNS"),
                    default_levels=(1500, 2000),
                    default_value=(1500, 2000),
                    unit=_("ms"),
                ),
            ),
            (
                "time_consumed_by_rule_engine",
                SimpleLevels(
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
                    title=_("Upper levels for the number of HTTP requests per second"),
                    default_levels=(500.0, 1000.0),
                    default_value=(500.0, 1000.0),
                    default_difference=(10.0, 20.0),
                    unit="per second",
                ),
            ),
            (
                "client_requests_https",
                Levels(
                    title=_("Upper levels for the number of HTTPS request per second"),
                    default_levels=(500.0, 1000.0),
                    default_value=(500.0, 1000.0),
                    default_difference=(10.0, 20.0),
                    unit="per second",
                ),
            ),
            (
                "client_requests_httpv2",
                Levels(
                    title=_("Upper levels for the number of HTTP/2 requests per second"),
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
        title=lambda: _("Web gateway miscellaneous"),
    )
)
