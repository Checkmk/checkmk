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


def _item_spec_cooling_cap():
    return TextInput(
        title=_("Cooling device"),
        help=_("This name corresponds to the cooling device to be monitored."),
        allow_empty=True,
    )


def _parameter_valuespec_cooling_cap():
    return Dictionary(
        elements=[
            (
                "min_capacity",
                Tuple(
                    title=_("Minimal cooling capacity"),
                    elements=[
                        Percentage(title=_("Warning if below")),
                        Percentage(title=_("Critical if below")),
                    ],
                ),
            ),
            (
                "max_capacity",
                Tuple(
                    title=_("Maximal cooling capacity"),
                    elements=[
                        Percentage(title=_("Warning if above")),
                        Percentage(title=_("Critical if above")),
                    ],
                ),
            ),
        ],
        help=_(
            "Here you can set different warn/crit levels regarding the available cooling "
            " capacity."
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="liebert_cooling",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_cooling_cap,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cooling_cap,
        title=lambda: _("Percentage of available cooling capacity"),
    )
)
