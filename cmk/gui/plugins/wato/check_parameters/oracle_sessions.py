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
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    Percentage,
    TextInput,
    Transform,
    Tuple,
)


def convert_oracle_sessions(value):
    if isinstance(value, tuple):
        return {"sessions_abs": value}
    if "sessions_abs" not in value:
        value["sessions_abs"] = (100, 200)
    return value


def _parameter_valuespec_oracle_sessions():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "sessions_abs",
                    Alternative(
                        title=_("Absolute levels of active sessions"),
                        help=_(
                            "This check monitors the current number of active sessions on Oracle"
                        ),
                        elements=[
                            FixedValue(
                                value=None, title=_("Do not use absolute levels"), totext=""
                            ),
                            Tuple(
                                title=_("Number of active sessions"),
                                elements=[
                                    Integer(
                                        title=_("Warning at"), unit=_("sessions"), default_value=100
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        unit=_("sessions"),
                                        default_value=200,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                (
                    "sessions_perc",
                    Tuple(
                        title=_("Relative levels of active sessions."),
                        help=_(
                            "Set upper levels of active sessions relative to max. number of sessions. This is optional."
                        ),
                        elements=[
                            Percentage(title=_("Warning at")),
                            Percentage(title=_("Critical at")),
                        ],
                    ),
                ),
            ],
            optional_keys=["sessions_perc"],
        ),
        forth=convert_oracle_sessions,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_sessions",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Database name"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_oracle_sessions,
        title=lambda: _("Oracle Sessions"),
    )
)
