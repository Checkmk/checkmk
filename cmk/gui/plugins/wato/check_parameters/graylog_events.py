#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Integer, Tuple


def _parameter_valuespec_graylog_events():
    return Dictionary(
        elements=[
            (
                "events_upper",
                Tuple(
                    title=_("Total events count upper levels"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "events_lower",
                Tuple(
                    title=_("Total events count lower levels"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "events_in_range_upper",
                Tuple(
                    title=_("Number of events in defined timespan upper level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="events"),
                        Integer(title=_("Critical below"), unit="events"),
                    ],
                ),
            ),
            (
                "events_in_range_lower",
                Tuple(
                    title=_("Number of events in defined timespan lower level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="events"),
                        Integer(title=_("Critical at"), unit="events"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="graylog_events",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_events,
        title=lambda: _("Graylog events"),
    )
)
