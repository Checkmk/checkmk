#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary, Integer


def _parameter_valuespec_windows_updates() -> Dictionary:
    return Dictionary(
        title=_("Parameters for the Windows Update Check with WSUS"),
        help=_("Set the according numbers to 0 if you want to disable alerting."),
        elements=[
            (
                "levels_important",
                SimpleLevels(
                    Integer, title=_("Levels for pending important updates"), default_value=(1, 1)
                ),
            ),
            (
                "levels_optional",
                SimpleLevels(
                    Integer, title=_("Levels for pending optional updates"), default_value=(1, 99)
                ),
            ),
            (
                "levels_lower_forced_reboot",
                SimpleLevels(
                    Age,
                    title=_("Levels for time until forced reboot due to pending important updates"),
                    default_value=(604800, 172800),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="windows_updates",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_windows_updates,
        title=lambda: _("WSUS (Windows Updates)"),
    )
)
