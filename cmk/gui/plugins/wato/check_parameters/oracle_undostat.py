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
from cmk.gui.valuespec import Age, Dictionary, MonitoringState, TextInput, Tuple


def _parameter_valuespec_oracle_undostat():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels for remaining undo retention"),
                    elements=[
                        Age(title=_("warning if less then"), default_value=600),
                        Age(title=_("critical if less then"), default_value=300),
                    ],
                ),
            ),
            (
                "nospaceerrcnt_state",
                MonitoringState(
                    default_value=2,
                    title=_("State in case of non space error count is greater then 0: "),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_undostat",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database SID"), size=12, allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_undostat,
        title=lambda: _("Oracle Undo Retention"),
    )
)
