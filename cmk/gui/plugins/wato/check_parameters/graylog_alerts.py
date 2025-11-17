#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Kuhn & Rueß GmbH
Consulting and Development
https://kuhn-ruess.de
"""


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_graylog_alerts():
    return Dictionary(
        elements=[
            (
                "alerts_upper",
                Tuple(
                    title=_("Total alerts count upper levels"),
                    elements=[
                        Integer(title=_("Warning at"), unit="alerts"),
                        Integer(title=_("Critical at"), unit="alerts"),
                    ],
                ),
            ),
            (
                "alerts_lower",
                Tuple(
                    title=_("Total alerts count lower levels"),
                    elements=[
                        Integer(title=_("Warning below"), unit="alerts"),
                        Integer(title=_("Critical below"), unit="alerts"),
                    ],
                ),
            ),
            (
                "events_upper",
                Tuple(
                    title=_("Total events count upper levesl"),
                    elements=[
                        Integer(title=_("Warning at"), unit="events"),
                        Integer(title=_("Critical at"), unit="events"),
                    ],
                ),
            ),
            (
                "events_lower",
                Tuple(
                    title=_("Total event count lower levels"),
                    elements=[
                        Integer(title=_("Warning below"), unit="events"),
                        Integer(title=_("Critical below"), unit="events"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_alerts",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_alerts,
        title=lambda: _("Graylog alerts"),
    )
)
