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
from cmk.gui.valuespec import Checkbox, Dictionary, TextInput


def _parameter_valuespec_brocade_optical():
    return Dictionary(
        elements=[
            ("temp", Checkbox(title=_("Temperature Alert"), default_value=True)),
            (
                "tx_light",
                Checkbox(title=_("TX Light alert"), label=_("TX Light alert"), default_value=False),
            ),
            (
                "rx_light",
                Checkbox(title=_("RX Light alert"), label=_("TX Light alert"), default_value=False),
            ),
            (
                "lanes",
                Checkbox(
                    title=_("Lanes"),
                    label=_("Monitor & Graph Lanes"),
                    help=_("Monitor and graph the lanes, if the port has multiple"),
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="brocade_optical",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Interface id")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_brocade_optical,
        title=lambda: _("Brocade Optical Signal"),
    )
)
