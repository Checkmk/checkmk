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
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _item_spec_clr_memory():
    return TextInput(
        title=_("Name of the Application"),
        help=_("The name of the DotNet (.Net) application or _Global_"),
        allow_empty=False,
    )


def _parameter_valuespec_clr_memory():
    return Dictionary(
        help=_(
            "This rule allows to set the warn and crit levels of the memory "
            "metrics of the DotNet (.Net) Runtime"
        ),
        elements=[
            (
                "upper",
                Tuple(
                    title=_("Percent time spent in garbage collection"),
                    elements=[
                        Percentage(title=_("Warning at"), label=_("% time"), default_value=10.0),
                        Percentage(title=_("Critical at"), label=_("% time"), default_value=15.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="clr_memory",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_clr_memory,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_clr_memory,
        title=lambda: _("DotNet (.Net) runtime memory levels"),
    )
)
