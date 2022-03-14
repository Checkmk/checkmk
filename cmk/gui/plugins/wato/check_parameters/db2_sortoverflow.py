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


def _item_spec_db2_sortoverflow():
    return TextInput(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    )


def _parameter_valuespec_db2_sortoverflow():
    return Dictionary(
        help=_("This rule allows you to set percentual limits for sort overflows."),
        elements=[
            (
                "levels_perc",
                Tuple(
                    title=_("Overflows"),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%"), default_value=2.0),
                        Percentage(title=_("Critical at"), unit=_("%"), default_value=4.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_sortoverflow",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_sortoverflow,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_sortoverflow,
        title=lambda: _("DB2 Sort Overflow"),
    )
)
