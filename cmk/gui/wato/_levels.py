#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    Percentage,
    Transform,
    Tuple,
    ValueSpec,
)


# The following function looks like a value spec and in fact
# can be used like one (but take no parameters)
def PredictiveLevels(
    default_difference: tuple[float, float] = (2.0, 4.0), unit: str = ""
) -> Transform:
    dif = default_difference
    unitname = unit
    if unitname:
        unitname += " "

    INJECTION_KEY = "__injected__"
    return Transform(
        Dictionary(
            title=_("Predictive levels (only on CMC)"),
            ignored_keys=[
                # This is a place holder:
                # The backend uses this marker to inject a callback to get the prediction.
                # Its main purpose it to bind the host name and service name,
                # which are not known to the plugin.
                INJECTION_KEY,
            ],
            optional_keys=[
                "weight",
                "levels_upper",
                "levels_upper_min",
                "levels_lower",
                "levels_lower_max",
            ],
            default_keys=["levels_upper"],
            columns=1,
            elements=[
                (
                    "period",
                    DropdownChoice(
                        title=_("Base prediction on"),
                        choices=[
                            ("wday", _("Day of the week (1-7, 1 is Monday)")),
                            ("day", _("Day of the month (1-31)")),
                            ("hour", _("Hour of the day (0-23)")),
                            ("minute", _("Minute of the hour (0-59)")),
                        ],
                    ),
                ),
                (
                    "horizon",
                    Integer(
                        title=_("Time horizon"),
                        unit=_("days"),
                        minvalue=1,
                        default_value=90,
                    ),
                ),
                # ( "weight",
                #   Percentage(
                #       title = _("Raise weight of recent time"),
                #       label = _("by"),
                #       default_value = 0,
                # )),
                (
                    "levels_upper",
                    CascadingDropdown(
                        title=_("Dynamic levels - upper bound"),
                        choices=[
                            (
                                "absolute",
                                _("Absolute difference from prediction"),
                                Tuple(
                                    elements=[
                                        Float(
                                            title=_("Warning at"),
                                            unit=unitname + _("above predicted value"),
                                            default_value=dif[0],
                                        ),
                                        Float(
                                            title=_("Critical at"),
                                            unit=unitname + _("above predicted value"),
                                            default_value=dif[1],
                                        ),
                                    ]
                                ),
                            ),
                            (
                                "relative",
                                _("Relative difference from prediction"),
                                Tuple(
                                    elements=[
                                        Percentage(
                                            title=_("Warning at"),
                                            # xgettext: no-python-format
                                            unit=_("% above predicted value"),
                                            default_value=10,
                                        ),
                                        Percentage(
                                            title=_("Critical at"),
                                            # xgettext: no-python-format
                                            unit=_("% above predicted value"),
                                            default_value=20,
                                        ),
                                    ]
                                ),
                            ),
                            (
                                "stdev",
                                _("In relation to standard deviation"),
                                Tuple(
                                    elements=[
                                        Float(
                                            title=_("Warning at"),
                                            unit=_(
                                                "times the standard deviation above the predicted value"
                                            ),
                                            default_value=2.0,
                                        ),
                                        Float(
                                            title=_("Critical at"),
                                            unit=_(
                                                "times the standard deviation above the predicted value"
                                            ),
                                            default_value=4.0,
                                        ),
                                    ]
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "levels_upper_min",
                    Tuple(
                        title=_("Limit for upper bound dynamic levels"),
                        help=_(
                            "Regardless of how the dynamic levels upper bound are computed according to the prediction: "
                            "the will never be set below the following limits. This avoids false alarms "
                            "during times where the predicted levels would be very low."
                        ),
                        elements=[
                            Float(title=_("Warning level is at least"), unit=unitname),
                            Float(title=_("Critical level is at least"), unit=unitname),
                        ],
                    ),
                ),
                (
                    "levels_lower",
                    CascadingDropdown(
                        title=_("Dynamic levels - lower bound"),
                        choices=[
                            (
                                "absolute",
                                _("Absolute difference from prediction"),
                                Tuple(
                                    elements=[
                                        Float(
                                            title=_("Warning at"),
                                            unit=unitname + _("below predicted value"),
                                            default_value=2.0,
                                        ),
                                        Float(
                                            title=_("Critical at"),
                                            unit=unitname + _("below predicted value"),
                                            default_value=4.0,
                                        ),
                                    ]
                                ),
                            ),
                            (
                                "relative",
                                _("Relative difference from prediction"),
                                Tuple(
                                    elements=[
                                        Percentage(
                                            title=_("Warning at"),
                                            # xgettext: no-python-format
                                            unit=_("% below predicted value"),
                                            default_value=10,
                                        ),
                                        Percentage(
                                            title=_("Critical at"),
                                            # xgettext: no-python-format
                                            unit=_("% below predicted value"),
                                            default_value=20,
                                        ),
                                    ]
                                ),
                            ),
                            (
                                "stdev",
                                _("In relation to standard deviation"),
                                Tuple(
                                    elements=[
                                        Float(
                                            title=_("Warning at"),
                                            unit=_(
                                                "times the standard deviation below the predicted value"
                                            ),
                                            default_value=2.0,
                                        ),
                                        Float(
                                            title=_("Critical at"),
                                            unit=_(
                                                "times the standard deviation below the predicted value"
                                            ),
                                            default_value=4.0,
                                        ),
                                    ]
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
        back=lambda p: {INJECTION_KEY: None, **p},
    )


# To be used as ValueSpec for levels on numeric values, with
# prediction
def Levels(
    help: str | None = None,
    default_levels: tuple[float, float] = (0.0, 0.0),
    default_difference: tuple[float, float] = (0.0, 0.0),
    default_value: tuple[float, float] | None = None,
    title: str | None = None,
    unit: str = "",
) -> Alternative:
    def match_levels_alternative(v: dict[Any, Any] | tuple[Any, Any]) -> int:
        if isinstance(v, dict):
            return 2
        if isinstance(v, tuple) and v != (None, None):
            return 1
        return 0

    if not isinstance(unit, str):
        raise ValueError(f"illegal unit for Levels: {unit}, expected a string")

    if default_value is None:
        default_value = default_levels

    elements: Sequence[ValueSpec[Any]] = [
        FixedValue(
            value=None,
            title=_("No Levels"),
            totext=_("Do not impose levels, always be OK"),
        ),
        Tuple(
            title=_("Fixed Levels"),
            elements=[
                Float(
                    unit=unit,
                    title=_("Warning at"),
                    default_value=default_levels[0],
                    allow_int=True,
                ),
                Float(
                    unit=unit,
                    title=_("Critical at"),
                    default_value=default_levels[1],
                    allow_int=True,
                ),
            ],
        ),
        PredictiveLevels(default_difference=default_difference, unit=unit),
    ]

    return Alternative(
        title=title,
        help=help,
        elements=elements,
        match=match_levels_alternative,
        default_value=default_value,
    )
