#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, Dictionary, ListOfStrings, Tuple


def _parameter_valuespec_win_license():
    return Dictionary(
        elements=[
            (
                "status",
                ListOfStrings(
                    title=_("Allowed license states"),
                    help=_("Here you can specify the allowed license states for windows."),
                    default_value=["Licensed", "Initial grace period"],
                ),
            ),
            (
                "expiration_time",
                Tuple(
                    title=_("Time until license expiration"),
                    help=_("Remaining days until the Windows license expires"),
                    elements=[
                        Age(title=_("Warning at"), default_value=14 * 24 * 60 * 60),
                        Age(title=_("Critical at"), default_value=7 * 24 * 60 * 60),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="win_license",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_win_license,
        title=lambda: _("Windows License"),
    )
)
