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


def _parameter_valuespec_winperf_ts_sessions():
    return Dictionary(
        help=_("This check monitors number of active and inactive terminal " "server sessions."),
        elements=[
            (
                "active",
                Tuple(
                    title=_("Number of active sessions"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("sessions"), default_value=100),
                        Integer(title=_("Critical at"), unit=_("sessions"), default_value=200),
                    ],
                ),
            ),
            (
                "inactive",
                Tuple(
                    title=_("Number of inactive sessions"),
                    help=_("Levels for the number of sessions that are currently inactive"),
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
        check_group_name="winperf_ts_sessions",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_winperf_ts_sessions,
        title=lambda: _("Windows Terminal Server Sessions"),
    )
)
