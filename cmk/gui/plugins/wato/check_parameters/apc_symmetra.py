#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Union

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    Integer,
    MonitoringState,
    Percentage,
    Transform,
    Tuple,
)


def _apc_symentra_transform_apc_symmetra(
    params: Union[list[float], tuple[float, ...], dict[str, Any]],
) -> dict[str, Any]:
    """
    >>> _apc_symentra_transform_apc_symmetra((1, 2, 3, 4))
    {'capacity': (1, 1)}
    >>> _apc_symentra_transform_apc_symmetra({"levels": (1, 2, 3, 4)})
    {'capacity': (1, 1)}
    >>> _apc_symentra_transform_apc_symmetra({"capacity": (95, 80), "output_load": (23, 42)})
    {'capacity': (95, 80)}
    """
    if isinstance(params, dict):
        if "levels" not in params:
            return {k: v for k, v in params.items() if k != "output_load"}
        cap, *_rest = params["levels"]
    else:
        cap, *_rest = params

    return {"capacity": (cap, cap)}


def _parameter_valuespec_apc_symentra():
    return Transform(
        Dictionary(
            elements=[
                (
                    "capacity",
                    Tuple(
                        title=_("Levels of battery capacity"),
                        elements=[
                            Percentage(
                                title=_("Warning below"),
                                default_value=95.0,
                            ),
                            Percentage(
                                title=_("Critical below"),
                                default_value=80.0,
                            ),
                        ],
                    ),
                ),
                (
                    "calibration_state",
                    MonitoringState(
                        title=_("State if calibration is invalid"),
                        default_value=0,
                    ),
                ),
                (
                    "post_calibration_levels",
                    Dictionary(
                        title=_("Levels of battery parameters after calibration"),
                        help=_(
                            "After a battery calibration the battery capacity is reduced until the "
                            "battery is fully charged again. Here you can specify an alternative "
                            "lower level in this post-calibration phase. "
                            "Since apc devices remember the time of the last calibration only "
                            "as a date, the alternative lower level will be applied on the whole "
                            "day of the calibration until midnight. You can extend this time period "
                            "with an additional time span to make sure calibrations occuring just "
                            "before midnight do not trigger false alarms."
                        ),
                        elements=[
                            (
                                "altcapacity",
                                Percentage(
                                    title=_(
                                        "Alternative critical battery capacity after calibration"
                                    ),
                                    default_value=50,
                                ),
                            ),
                            (
                                "additional_time_span",
                                Integer(
                                    title=("Extend post-calibration phase by additional time span"),
                                    unit=_("minutes"),
                                    default_value=0,
                                ),
                            ),
                        ],
                        optional_keys=False,
                    ),
                ),
                (
                    "battime",
                    Tuple(
                        title=_("Time left on battery"),
                        elements=[
                            Age(
                                title=_("Warning at"),
                                help=_(
                                    "Time left on Battery at and below which a warning state is triggered"
                                ),
                                default_value=0,
                                display=["hours", "minutes"],
                            ),
                            Age(
                                title=_("Critical at"),
                                help=_(
                                    "Time Left on Battery at and below which a critical state is triggered"
                                ),
                                default_value=0,
                                display=["hours", "minutes"],
                            ),
                        ],
                    ),
                ),
                (
                    "battery_replace_state",
                    MonitoringState(
                        title=_("State if battery needs replacement"),
                        default_value=1,
                    ),
                ),
            ],
        ),
        forth=_apc_symentra_transform_apc_symmetra,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="apc_symentra",
        group=RulespecGroupCheckParametersEnvironment,
        parameter_valuespec=_parameter_valuespec_apc_symentra,
        title=lambda: _("APC Symmetra Checks"),
    )
)
