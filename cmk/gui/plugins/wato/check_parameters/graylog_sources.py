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
from cmk.gui.valuespec import Age, Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_graylog_sources():
    return Dictionary(
        elements=[
            (
                "msgs_upper",
                Tuple(
                    title=_("Total message count upper levels"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "msgs_lower",
                Tuple(
                    title=_("Total message count lower levels"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "msgs_avg",
                Integer(
                    title=_("Message averaging"),
                    help=_(
                        "By activating averaging, Check_MK will compute the average of "
                        "the message count over a given interval. If you define "
                        "alerting levels they will automatically be applied on the "
                        "averaged value. This helps to mask out short peaks."
                    ),
                    unit=_("minutes"),
                    minvalue=1,
                    default_value=30,
                ),
            ),
            (
                "msgs_avg_upper",
                Tuple(
                    title=_("Average message count upper levels"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "msgs_avg_lower",
                Tuple(
                    title=_("Average message count lower levels"),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "msgs_diff",
                Age(
                    title=_("Timespan for difference calculation of total number of " "messages"),
                    display=["days", "hours", "minutes"],
                    default_value=1800,
                ),
            ),
            (
                "msgs_diff_lower",
                Tuple(
                    title=_("Number of messages in defined timespan lower level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="messages"),
                        Integer(title=_("Critical below"), unit="messages"),
                    ],
                ),
            ),
            (
                "msgs_diff_upper",
                Tuple(
                    title=_("Number of messages in defined timespan upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="messages"),
                        Integer(title=_("Critical at"), unit="messages"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="graylog_sources",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Source name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_graylog_sources,
        title=lambda: _("Graylog sources"),
    )
)
