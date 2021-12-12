#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _item_spec_cooling_pos():
    return TextInput(
        title=_("Cooling device"),
        help=_("This name corresponds to the cooling device to be monitored."),
        allow_empty=True,
    )


def _parameter_valuespec_cooling_pos():
    return Dictionary(
        elements=[
            (
                "min_capacity",
                Tuple(
                    title=_("Minimal free cooling positions"),
                    elements=[
                        Percentage(title=_("Warning if below")),
                        Percentage(title=_("Critical if below")),
                    ],
                ),
            ),
            (
                "max_capacity",
                Tuple(
                    title=_("Maximal free cooling positions"),
                    elements=[
                        Percentage(title=_("Warning if above")),
                        Percentage(title=_("Critical if above")),
                    ],
                ),
            ),
        ],
        help=_(
            "Here you can set different warn/crit levels regarding the free cooling " " positions."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="liebert_cooling_position",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_cooling_pos,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cooling_pos,
        title=lambda: _("Percentage of free cooling positions"),
    )
)
