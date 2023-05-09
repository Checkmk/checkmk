#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)


def transform_humidity(p):
    if isinstance(p, (list, tuple)):
        p = {
            "levels_lower": (float(p[1]), float(p[0])),
            "levels": (float(p[2]), float(p[3])),
        }
    return p


def _item_spec_humidity():
    return TextAscii(
        title=_("Sensor name"),
        help=_("The identifier of the sensor."),
    )


def _parameter_valuespec_humidity():
    return Transform(
        Dictionary(
            help=_("This Ruleset sets the threshold limits for humidity sensors"),
            elements=[
                ("levels",
                 Tuple(
                     title=_("Upper levels"),
                     elements=[
                         Percentage(title=_("Warning at")),
                         Percentage(title=_("Critical at")),
                     ],
                 )),
                ("levels_lower",
                 Tuple(
                     title=_("Lower levels"),
                     elements=[
                         Percentage(title=_("Warning below")),
                         Percentage(title=_("Critical below")),
                     ],
                 )),
            ],
        ),
        forth=transform_humidity,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="humidity",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_humidity,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_humidity,
        title=lambda: _("Humidity Levels"),
    ))
