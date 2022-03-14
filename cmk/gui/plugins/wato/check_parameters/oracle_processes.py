#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _parameter_valuespec_oracle_processes():
    return Dictionary(
        help=_(
            "Here you can override the default levels for the ORACLE Processes check. The levels "
            "are applied on the number of used processes in percentage of the configured limit."
        ),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels for used processes"),
                    elements=[
                        Percentage(title=_("Warning if more than"), default_value=70.0),
                        Percentage(title=_("Critical if more than"), default_value=90.0),
                    ],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_processes",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database SID"), size=12, allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_processes,
        title=lambda: _("Oracle Processes"),
    )
)
