#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, ListChoice, Tuple

bluecat_operstates = [
    (1, "running normally"),
    (2, "not running"),
    (3, "currently starting"),
    (4, "currently stopping"),
    (5, "fault"),
]


def _parameter_valuespec_bluecat_ntp():
    return Dictionary(
        elements=[
            (
                "oper_states",
                Dictionary(
                    title=_("Operations States"),
                    elements=[
                        (
                            "warning",
                            ListChoice(
                                title=_("States treated as warning"),
                                choices=bluecat_operstates,
                                default_value=[2, 3, 4],
                            ),
                        ),
                        (
                            "critical",
                            ListChoice(
                                title=_("States treated as critical"),
                                choices=bluecat_operstates,
                                default_value=[5],
                            ),
                        ),
                    ],
                    required_keys=["warning", "critical"],
                ),
            ),
            (
                "stratum",
                Tuple(
                    title=_("Levels for Stratum "),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="bluecat_ntp",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_bluecat_ntp,
        title=lambda: _("Bluecat NTP Settings"),
    )
)
