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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_jira_workflow():
    return Dictionary(
        elements=[
            (
                "workflow_count_lower",
                Tuple(
                    title=_("Total number of issues lower level"),
                    elements=[
                        Integer(title=_("Warning if less then"), unit="issues"),
                        Integer(title=_("Critical if less then"), unit="íssues"),
                    ],
                ),
            ),
            (
                "workflow_count_upper",
                Tuple(
                    title=_("Total number of issues upper level"),
                    elements=[
                        Integer(title=_("Warning at"), unit="issues"),
                        Integer(title=_("Critical at"), unit="issues"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jira_workflow",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Project and workflow name"),
            help=_("e.g. 'My_Project/Closed'"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jira_workflow,
        title=lambda: _("Jira workflow"),
    )
)
