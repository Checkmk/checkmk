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


def _parameter_valuespec_hw_fans_perc():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper fan speed levels"),
                    elements=[
                        Percentage(title=_("warning if at")),
                        Percentage(title=_("critical if at")),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower fan speed levels"),
                    elements=[
                        Percentage(title=_("warning if below")),
                        Percentage(title=_("critical if below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hw_fans_perc",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("Fan Name"), help=_("The identifier of the fan.")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_hw_fans_perc,
        title=lambda: _("Fan speed of hardware devices (in percent)"),
    )
)
