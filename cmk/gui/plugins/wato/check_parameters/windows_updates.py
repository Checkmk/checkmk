#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, Optional
from typing import Tuple as _Tuple
from typing import Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    Dictionary,
    FixedValue,
    Integer,
    Transform,
    Tuple,
    ValueSpec,
)


def _zero_to_none(n: int) -> Optional[float]:
    return n if n != 0 else None


def _align_levels(
    levels: _Tuple[Optional[float], Optional[float]]
) -> Optional[_Tuple[float, float]]:
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
def _transform(p: Union[tuple, dict]) -> Dict[str, Any]:
    if isinstance(p, dict):
        return p
    important_levels = (_zero_to_none(p[0]), _zero_to_none(p[1]))
    optional_levels = (_zero_to_none(p[2]), _zero_to_none(p[3]))
    return {
        "levels_important": _align_levels(important_levels),
        "levels_optional": _align_levels(optional_levels),
        "levels_lower_forced_reboot": (p[4], p[5]),
    }


def _NoLevels() -> FixedValue:
    return FixedValue(
        value=None,
        title=_("No Levels"),
        totext=_("Do not impose levels, always be OK"),
    )


def _FixedLevels(
    default_value: _Tuple[int, int],
) -> Tuple:
    return Tuple(
        title=_("Fixed Levels"),
        elements=[
            Integer(
                title=_("Warning at"),
                default_value=default_value[0],
            ),
            Integer(
                title=_("Critical at"),
                default_value=default_value[1],
            ),
        ],
    )


def _IntegerLevels(
    help: Optional[str] = None,  # pylint: disable=redefined-builtin
    title: Optional[str] = None,
    default_value: Optional[tuple[float, float]] = None,
) -> Alternative:
    def match_levels_alternative(v: Optional[_Tuple[float, float]]) -> int:
        if v is None:
            return 0
        return 1

    elements = [
        _NoLevels(),
        _FixedLevels(default_value=(1, 1)),
    ]
    return Alternative(
        title=title,
        help=help,
        elements=elements,
        match=match_levels_alternative,
        default_value=default_value,
    )


def _reboot_levels() -> Alternative:
    def match_levels_alternative(v: Optional[_Tuple[float, float]]) -> int:
        if v is None:
            return 0
        return 1

    elements = [
        _NoLevels(),
        Tuple(
            title=_("Fixed Levels"),
            elements=[
                Age(title=_("Warning at"), default_value=604800),
                Age(title=_("Critical at"), default_value=172800),
            ],
        ),
    ]
    return Alternative(
        title="Levels for time until forced reboot due to pending important updates",
        elements=elements,
        match=match_levels_alternative,
        default_value=(604800, 172800),
    )


def _parameter_valuespec_windows_updates() -> ValueSpec:
    return Transform(
        forth=_transform,
        valuespec=Dictionary(
            title=_("Parameters for the Windows Update Check with WSUS"),
            help=_("Set the according numbers to 0 if you want to disable alerting."),
            elements=[
                (
                    "levels_important",
                    _IntegerLevels(
                        title="Levels for pending important updates", default_value=(1, 1)
                    ),
                ),
                (
                    "levels_optional",
                    _IntegerLevels(
                        title="Levels for pending optional updates", default_value=(1, 99)
                    ),
                ),
                (
                    "levels_lower_forced_reboot",
                    _reboot_levels(),
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
