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
from cmk.gui.valuespec import Age, Dictionary, DropdownChoice, Integer


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
                # Configuration variable name below is intentionally kept stable.
                # Renaming it would require a cumbersome migration, which is outside the scope of the task.
                "levels_lower_forced_reboot",
                SimpleLevels(
                    Age,
                    title=_("Windows Update notification time"),
                    default_value=(604800, 172800),
                ),
            ),
            (
                "reboot_required_show_state",
                DropdownChoice[int | None](
                    choices=[
                        (None, _("Do not display reboot required state")),
                        (0, _("OK")),
                        (1, _("WARN")),
                        (2, _("CRIT")),
                        (3, _("UNKNOWN")),
                    ],
                    sorted=False,
                    title=_("Service state if reboot required"),
                    help=_(
                        "If a reboot is required, the selected status will be displayed. Default is warning."
                    ),
                    default_value=1,
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
