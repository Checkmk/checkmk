#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.mssql_blocked_sessions import mssql_waittypes
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DualListChoice, Float, MonitoringState, TextInput, Tuple


def _parameter_valuespec_mssql_instance_blocked_sessions():
    return Dictionary(
        elements=[
            (
                "state",
                MonitoringState(
                    title=_("State if at least one blocked session"),
                    default_value=2,
                ),
            ),
            (
                "waittime",
                Tuple(
                    title=_("Levels for wait"),
                    help=_(
                        "The threshholds for wait_duration_ms. Will "
                        "overwrite the default state set above."
                    ),
                    default_value=(0, 0),
                    elements=[
                        Float(title=_("Warning at"), unit=_("seconds"), display_format="%.3f"),
                        Float(title=_("Critical at"), unit=_("seconds"), display_format="%.3f"),
                    ],
                ),
            ),
            (
                "ignore_waittypes",
                DualListChoice(
                    title=_("Ignore wait types"),
                    rows=40,
                    choices=[(entry, entry) for entry in mssql_waittypes],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_instance_blocked_sessions",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Instance identifier")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_instance_blocked_sessions,
        title=lambda: _("MSSQL Blocked Sessions"),
    )
)
