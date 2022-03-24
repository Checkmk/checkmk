#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Optional, Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Age, Dictionary, Integer, Transform, ValueSpec


def _zero_to_none(n: int) -> Optional[float]:
    return n if n != 0 else None


def _align_levels(levels: tuple[Optional[float], Optional[float]]) -> Optional[tuple[float, float]]:
    warn, crit = levels
    if warn is None and crit is None:
        return None
    if warn is None and crit is not None:
        return (crit, crit)
    if warn is not None and crit is None:
        return (warn, 1000 * warn)
    if warn is not None and crit is not None:
        return (warn, crit)
    # cannot reach this but keep mypy happy
    return None


# Can/Should this be typed more specific? -> TypedDict
def _transform(p: Union[tuple, dict]) -> dict[str, Any]:
    if isinstance(p, dict):
        return p
    levels_important = (_zero_to_none(p[0]), _zero_to_none(p[1]))
    levels_optional = (_zero_to_none(p[2]), _zero_to_none(p[3]))
    return {
        "levels_important": _align_levels(levels_important),
        "levels_optional": _align_levels(levels_optional),
        "levels_lower_forced_reboot": (p[4], p[5]),
    }


def _parameter_valuespec_windows_updates() -> ValueSpec:
    return Transform(
        forth=_transform,
        valuespec=Dictionary(
            title=_("Parameters for the Windows Update Check with WSUS"),
            help=_("Set the according numbers to 0 if you want to disable alerting."),
            elements=[
                (
                    "levels_important",
                    SimpleLevels(
                        Integer, title="Levels for pending important updates", default_value=None
                    ),
                ),
                (
                    "levels_optional",
                    SimpleLevels(
                        Integer, title="Levels for pending important updates", default_value=None
                    ),
                ),
                (
                    "levels_lower_forced_reboot",
                    SimpleLevels(
                        Age,
                        title="Levels for time until forced reboot due to pending important updates",
                        default_value=(604800, 172800),
                    ),
                ),
            ],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="windows_updates",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_windows_updates,
        title=lambda: _("WSUS (Windows Updates)"),
    )
)
