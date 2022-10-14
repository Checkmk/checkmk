#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    TextInput,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Percentage


def _parameter_valuespec_cpu_reservation():
    return Dictionary(
        title=_("Levels CPU"),
        elements=[
            (
                "levels",
                SimpleLevels(Percentage, title=_("CPU reservation"), default_levels=(80.0, 90.0)),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cpu_reservation",
        item_spec=lambda: TextInput(title=_("CPU Reservation")),
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_cpu_reservation,
        title=lambda: _("CPU Reservation"),
    )
)
