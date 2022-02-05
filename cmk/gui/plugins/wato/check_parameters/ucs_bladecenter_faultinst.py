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
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameter_valuespec_ucs_bladecenter_faultinst():
    status_choices = [
        (0, _("Ok")),
        (1, _("Warning")),
        (2, _("Critical")),
        (3, _("Unknown")),
    ]
    return Dictionary(
        elements=[
            (
                "critical",
                DropdownChoice(
                    title=_("'Critical' state"),
                    choices=status_choices,
                    default_value=2,
                ),
            ),
            (
                "major",
                DropdownChoice(
                    title=_("'Major' state"),
                    choices=status_choices,
                    default_value=1,
                ),
            ),
            (
                "warning",
                DropdownChoice(
                    title=_("'Warning' state"),
                    choices=status_choices,
                    default_value=1,
                ),
            ),
            (
                "minor",
                DropdownChoice(
                    title=_("'Minor' state"),
                    choices=status_choices,
                    default_value=1,
                ),
            ),
            (
                "info",
                DropdownChoice(
                    title=_("'Info' state"),
                    choices=status_choices,
                    default_value=0,
                ),
            ),
            (
                "condition",
                DropdownChoice(
                    title=_("'Condition' state"),
                    choices=status_choices,
                    default_value=0,
                ),
            ),
            (
                "cleared",
                DropdownChoice(
                    title=_("'Cleared' state"),
                    choices=status_choices,
                    default_value=0,
                ),
            ),
        ],
        title=_("Translate UCS Bladecenter state to monitoring state"),
        optional_keys=["critical", "major", "warning", "minor", "info", "condition", "cleared"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ucs_bladecenter_faultinst",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ucs_bladecenter_faultinst,
        title=lambda: _("UCS Bladecenter Fault instances"),
    )
)
