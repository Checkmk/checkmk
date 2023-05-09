#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    Checkbox,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersNetworking,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _parameter_valuespec_brocade_optical():
    return Dictionary(
        elements=[
            ('temp', Checkbox(title=_("Temperature Alert"), default_value=True)),
            ('tx_light',
             Checkbox(title=_("TX Light alert"), label=_("TX Light alert"), default_value=False)),
            ('rx_light',
             Checkbox(title=_("RX Light alert"), label=_("TX Light alert"), default_value=False)),
            ('lanes',
             Checkbox(title=_("Lanes"),
                      label=_("Monitor & Graph Lanes"),
                      help=_("Monitor and graph the lanes, if the port has multiple"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="brocade_optical",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextAscii(title=_("Interface id")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_brocade_optical,
        title=lambda: _("Brocade Optical Signal"),
    ))
