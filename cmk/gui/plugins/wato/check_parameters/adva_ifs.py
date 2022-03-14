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
from cmk.gui.valuespec import Dictionary, Float, TextInput, Tuple


def _item_spec_adva_ifs():
    return TextInput(
        title=_("Interface"),
        allow_empty=False,
    )


def _parameter_valuespec_adva_ifs():
    return Dictionary(
        elements=[
            (
                "limits_output_power",
                Tuple(
                    title=_("Sending Power"),
                    elements=[
                        Float(title=_("lower limit"), unit="dBm"),
                        Float(title=_("upper limit"), unit="dBm"),
                    ],
                ),
            ),
            (
                "limits_input_power",
                Tuple(
                    title=_("Received Power"),
                    elements=[
                        Float(title=_("lower limit"), unit="dBm"),
                        Float(title=_("upper limit"), unit="dBm"),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="adva_ifs",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_adva_ifs,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_adva_ifs,
        title=lambda: _("Adva Optical Transport Laser Power"),
    )
)
