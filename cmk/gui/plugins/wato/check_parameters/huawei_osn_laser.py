#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_huawei_osn_laser():
    return Dictionary(
        elements=[
            (
                "levels_low_in",
                Tuple(
                    title=_("Levels for laser input"),
                    default_value=(-160.0, -180.0),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
            (
                "levels_low_out",
                Tuple(
                    title=_("Levels for laser output"),
                    default_value=(-160.0, -180.0),
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="huawei_osn_laser",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Laser id")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_huawei_osn_laser,
        title=lambda: _("OSN Laser attenuation"),
    )
)
