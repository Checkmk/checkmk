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
from cmk.gui.valuespec import defines, Dictionary, ListOfTimeRanges, TextInput


def _item_spec_motion():
    return TextInput(
        title=_("Sensor name"),
        help=_("The identifier of the sensor."),
    )


def _parameter_valuespec_motion():
    return Dictionary(
        elements=[
            (
                "time_periods",
                Dictionary(
                    title=_("Time periods"),
                    help=_(
                        "Specifiy time ranges during which no motion is expected. "
                        "Outside these times, the motion detector will always be in "
                        "state OK"
                    ),
                    elements=[
                        (day_id, ListOfTimeRanges(title=day_str))
                        for day_id, day_str in defines.weekdays_by_name()
                    ],
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="motion",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=_item_spec_motion,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_motion,
        title=lambda: _("Motion Detectors"),
    )
)
