#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
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
