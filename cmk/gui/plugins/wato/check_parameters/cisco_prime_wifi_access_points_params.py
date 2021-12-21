#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_cisco_prime_wifi_access_points():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Maximum amount of non-operational access points"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=20.0),
                        Percentage(title=_("Critical at"), default_value=40.0),
                    ],
                ),
            ),
        ],
        required_keys=["levels"],  # There is only one value, so its required
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cisco_prime_wifi_access_points",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_prime_wifi_access_points,
        title=lambda: _("Cisco Prime WiFi Access Points"),
    )
)
