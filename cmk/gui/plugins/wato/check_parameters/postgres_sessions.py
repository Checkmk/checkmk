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
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_postgres_sessions():
    return Dictionary(
        help=_("This check monitors the current number of active and idle sessions on PostgreSQL"),
        elements=[
            (
                "total",
                Tuple(
                    title=_("Number of current sessions"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
                    ],
                ),
            ),
            (
                "running",
                Tuple(
                    title=_("Number of currently running sessions"),
                    help=_("Levels for the number of sessions that are currently active"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=10),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=20),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="postgres_sessions",
        group=RulespecGroupCheckParametersApplications,
        is_deprecated=True,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_postgres_sessions,
        title=lambda: _("PostgreSQL Sessions"),
    )
)
