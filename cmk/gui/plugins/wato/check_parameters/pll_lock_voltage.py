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
from cmk.gui.valuespec import Dictionary, DropdownChoice, Float, ListOf, Tuple


def _parameter_valuespec_pll_lock_voltage():
    return Dictionary(
        help=_("PLL lock voltages by freqency"),
        elements=[
            (
                "rx",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            Float(title=_("Frequencies up to"), unit="MHz"),
                            Float(title=_("Warning below"), unit="V"),
                            Float(title=_("Critical below"), unit="V"),
                            Float(title=_("Warning at or above"), unit="V"),
                            Float(title=_("Critical at or above"), unit="V"),
                        ],
                    ),
                    title=_("Lock voltages for RX PLL"),
                    help=_(
                        "Specify frequency ranges by the upper boundary of the range "
                        "to which the voltage levels are to apply. The list is sorted "
                        "automatically when saving."
                    ),
                    movable=False,
                ),
            ),
            (
                "tx",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            Float(title=_("Frequencies up to"), unit="MHz"),
                            Float(title=_("Warning below"), unit="V"),
                            Float(title=_("Critical below"), unit="V"),
                            Float(title=_("Warning at or above"), unit="V"),
                            Float(title=_("Critical at or above"), unit="V"),
                        ],
                    ),
                    title=_("Lock voltages for TX PLL"),
                    help=_(
                        "Specify frequency ranges by the upper boundary of the range "
                        "to which the voltage levels are to apply. The list is sorted "
                        "automatically when saving."
                    ),
                    movable=False,
                ),
            ),
        ],
        optional_keys=["rx", "tx"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="pll_lock_voltage",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: DropdownChoice(
            title=_("RX/TX"), choices=[("RX", _("RX")), ("TX", _("TX"))]
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_pll_lock_voltage,
        title=lambda: _("Lock Voltage for PLLs"),
    )
)
