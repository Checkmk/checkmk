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
from cmk.gui.valuespec import Age, Dictionary, Float, Integer, TextInput, Tuple


def _parameter_valuespec_jira_custom_svc():
    return Dictionary(
        elements=[
            (
                "count_diff",
                Age(
                    title=_("Timespan for difference calculation of total number of issues"),
                    display=["days", "hours", "minutes"],
                    default_value=86400 * 7,
                ),
            ),
            (
                "custom_svc_count_lower",
                Tuple(
                    title=_("Total number of issues lower level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="issues"),
                        Integer(title=_("Critical below"), unit="íssues"),
                    ],
                ),
            ),
            (
                "custom_svc_count_upper",
                Tuple(
                    title=_("Total number of issues upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="issues"),
                        Integer(title=_("Critical at"), unit="issues"),
                    ],
                ),
            ),
            (
                "count_diff_lower",
                Tuple(
                    title=_("Difference on total number of issues lower level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="issues"),
                        Integer(title=_("Critical below"), unit="íssues"),
                    ],
                ),
            ),
            (
                "count_diff_upper",
                Tuple(
                    title=_("Difference on total number of issues upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="issues"),
                        Integer(title=_("Critical at"), unit="issues"),
                    ],
                ),
            ),
            (
                "sum_diff",
                Age(
                    title=_("Timespan for difference calculation of summed up values"),
                    display=["days", "hours", "minutes"],
                    default_value=86400 * 7,
                ),
            ),
            (
                "custom_svc_sum_lower",
                Tuple(
                    title=_("Summed up values lower level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="issues"),
                        Integer(title=_("Critical below"), unit="íssues"),
                    ],
                ),
            ),
            (
                "custom_svc_sum_upper",
                Tuple(
                    title=_("Summed up values upper level"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "sum_diff_lower",
                Tuple(
                    title=_("Difference on summed up values lower level"),
                    elements=[
                        Integer(title=_("Warning below"), unit="issues"),
                        Integer(title=_("Critical below"), unit="íssues"),
                    ],
                ),
            ),
            (
                "sum_diff_upper",
                Tuple(
                    title=_("Difference on summed up values upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="issues"),
                        Integer(title=_("Critical at"), unit="issues"),
                    ],
                ),
            ),
            (
                "custom_svc_avg_lower",
                Tuple(
                    title=_("Averaged values lower level"),
                    elements=[Float(title=_("Warning below")), Float(title=_("Critical below"))],
                ),
            ),
            (
                "custom_svc_avg_upper",
                Tuple(
                    title=_("Averaged values upper level"),
                    elements=[Float(title=_("Warning at")), Float(title=_("Critical at"))],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jira_custom_svc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Custom service name"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jira_custom_svc,
        title=lambda: _("Jira custom service"),
    )
)
