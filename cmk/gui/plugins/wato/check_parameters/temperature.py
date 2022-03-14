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
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Float,
    Integer,
    TextInput,
    Transform,
    Tuple,
)


# New temperature rule for modern temperature checks that have the
# sensor type (e.g. "CPU", "Chassis", etc.) as the beginning of their
# item (e.g. "CPU 1", "Chassis 17/11"). This will replace all other
# temperature rulesets in future. Note: those few temperature checks
# that do *not* use an item, need to be converted to use one single
# item (other than None).
def _parameter_valuespec_temperature():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Transform(
                        valuespec=Tuple(
                            title=_("Upper Temperature Levels"),
                            elements=[
                                Float(title=_("Warning at"), unit="°C", default_value=26),
                                Float(title=_("Critical at"), unit="°C", default_value=30),
                            ],
                        ),
                        forth=lambda elems: (float(elems[0]), float(elems[1])),
                    ),
                ),
                (
                    "levels_lower",
                    Transform(
                        valuespec=Tuple(
                            title=_("Lower Temperature Levels"),
                            elements=[
                                Float(title=_("Warning below"), unit="°C", default_value=0),
                                Float(title=_("Critical below"), unit="°C", default_value=-10),
                            ],
                        ),
                        forth=lambda elems: (float(elems[0]), float(elems[1])),
                    ),
                ),
                (
                    "output_unit",
                    DropdownChoice(
                        title=_("Display values in "),
                        choices=[
                            ("c", _("Celsius")),
                            ("f", _("Fahrenheit")),
                            ("k", _("Kelvin")),
                        ],
                    ),
                ),
                (
                    "input_unit",
                    DropdownChoice(
                        title=_("Override unit of sensor"),
                        help=_(
                            "In some rare cases the unit that is signalled by the sensor "
                            "is wrong and e.g. the sensor sends values in Fahrenheit while "
                            "they are misinterpreted as Celsius. With this setting you can "
                            "force the reading of the sensor to be interpreted as customized. "
                        ),
                        choices=[
                            ("c", _("Celsius")),
                            ("f", _("Fahrenheit")),
                            ("k", _("Kelvin")),
                        ],
                    ),
                ),
                (
                    "device_levels_handling",
                    DropdownChoice(
                        title=_("Interpretation of the device's own temperature status"),
                        choices=[
                            ("usr", _("Ignore device's own levels")),
                            ("dev", _("Only use device's levels, ignore yours")),
                            ("best", _("Use least critical of your and device's levels")),
                            ("worst", _("Use most critical of your and device's levels")),
                            ("devdefault", _("Use device's levels if present, otherwise yours")),
                            (
                                "usrdefault",
                                _("Use your own levels if present, otherwise the device's"),
                            ),
                        ],
                        default_value="usrdefault",
                    ),
                ),
                (
                    "trend_compute",
                    Dictionary(
                        title=_("Trend computation"),
                        elements=[
                            (
                                "period",
                                Integer(
                                    title=_("Observation period for temperature trend computation"),
                                    default_value=30,
                                    minvalue=5,
                                    unit=_("minutes"),
                                ),
                            ),
                            (
                                "trend_levels",
                                Tuple(
                                    title=_("Levels on temperature increase per period"),
                                    elements=[
                                        Integer(
                                            title=_("Warning at"),
                                            unit="°C / " + _("period"),
                                            default_value=5,
                                        ),
                                        Integer(
                                            title=_("Critical at"),
                                            unit="°C / " + _("period"),
                                            default_value=10,
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "trend_levels_lower",
                                Tuple(
                                    title=_("Levels on temperature decrease per period"),
                                    elements=[
                                        Integer(
                                            title=_("Warning at"),
                                            unit="°C / " + _("period"),
                                            default_value=5,
                                        ),
                                        Integer(
                                            title=_("Critical at"),
                                            unit="°C / " + _("period"),
                                            default_value=10,
                                        ),
                                    ],
                                ),
                            ),
                            (
                                "trend_timeleft",
                                Tuple(
                                    title=_(
                                        "Levels on the time left until a critical temperature (upper or lower) is reached"
                                    ),
                                    elements=[
                                        Integer(
                                            title=_("Warning if below"),
                                            unit=_("minutes"),
                                            default_value=240,
                                        ),
                                        Integer(
                                            title=_("Critical if below"),
                                            unit=_("minutes"),
                                            default_value=120,
                                        ),
                                    ],
                                ),
                            ),
                        ],
                        optional_keys=["trend_levels", "trend_levels_lower", "trend_timeleft"],
                    ),
                ),
            ],
            ignored_keys=["_item_key"],
        ),
        forth=lambda v: isinstance(v, tuple) and {"levels": v} or v,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="temperature",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(
            title=_("Sensor ID"), help=_("The identifier of the thermal sensor.")
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_temperature,
        title=lambda: _("Temperature"),
    )
)
