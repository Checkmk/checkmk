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
from cmk.gui.valuespec import Dictionary, DropdownChoice, Integer, Tuple


def _parameter_valuespec_sles_license():
    return Dictionary(
        elements=[
            (
                "status",
                DropdownChoice(
                    title=_("Status"),
                    help=_("Status of the SLES license"),
                    choices=[
                        ("Registered", _("Registered")),
                        ("Ignore", _("Do not check")),
                    ],
                ),
            ),
            (
                "subscription_status",
                DropdownChoice(
                    title=_("Subscription"),
                    help=_("Status of the SLES subscription"),
                    choices=[
                        ("ACTIVE", _("ACTIVE")),
                        ("Ignore", _("Do not check")),
                    ],
                ),
            ),
            (
                "days_left",
                Tuple(
                    title=_("Time until license expiration"),
                    help=_("Remaining days until the SLES license expires"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("days")),
                        Integer(title=_("Critical at"), unit=_("days")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="sles_license",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_sles_license,
        title=lambda: _("SLES License"),
    )
)
