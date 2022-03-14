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
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _parameter_valuespec_generic_rate():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels"),
                    elements=[
                        Float(title="Warning at", unit="/s"),
                        Float(title="Critical at", unit="/s"),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Float(title="Warning below", unit="/s"),
                        Float(title="Critical below", unit="/s"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="generic_rate",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(
            title=_("Item"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_generic_rate,
        title=lambda: _("Generic rate"),
    )
)
