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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_pdu_gude():
    return Dictionary(
        elements=[
            (
                "kWh",
                Tuple(
                    title=_("Total accumulated Active Energy of Power Channel"),
                    elements=[
                        Integer(title=_("warning at"), unit=_("kW")),
                        Integer(title=_("critical at"), unit=_("kW")),
                    ],
                ),
            ),
            (
                "W",
                Tuple(
                    title=_("Active Power"),
                    elements=[
                        Integer(title=_("warning at"), unit=_("W")),
                        Integer(title=_("critical at"), unit=_("W")),
                    ],
                ),
            ),
            (
                "A",
                Tuple(
                    title=_("Current on Power Channel"),
                    elements=[
                        Integer(title=_("warning at"), unit=_("A")),
                        Integer(title=_("critical at"), unit=_("A")),
                    ],
                ),
            ),
            (
                "V",
                Tuple(
                    title=_("Voltage on Power Channel"),
                    elements=[
                        Integer(title=_("warning if below"), unit=_("V")),
                        Integer(title=_("critical if below"), unit=_("V")),
                    ],
                ),
            ),
            (
                "VA",
                Tuple(
                    title=_("Line Mean Apparent Power"),
                    elements=[
                        Integer(title=_("warning at"), unit=_("VA")),
                        Integer(title=_("critical at"), unit=_("VA")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="pdu_gude",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(
            title=_("Phase Number"), help=_("The Number of the power Phase.")
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_pdu_gude,
        title=lambda: _("Levels for Gude PDU Devices"),
    )
)
