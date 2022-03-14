#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _parameter_valuespec_fpga_utilization():
    return Dictionary(
        help=_("Give FPGA utilization levels in percent. The possible range is from 0% to 100%."),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Alert on too high FPGA utilization"),
                    elements=[
                        Percentage(title=_("Warning at a utilization of"), default_value=80.0),
                        Percentage(title=_("Critical at a utilization of"), default_value=90.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fpga_utilization",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("FPGA"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fpga_utilization,
        title=lambda: _("FPGA utilization"),
    )
)
