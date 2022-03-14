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
from cmk.gui.valuespec import Dictionary, ListOf, MonitoringState, TextInput, Tuple


def _parameter_valuespec_cisco_wlc():
    return Dictionary(
        help=_(
            "Here you can set which alert type is set when the given "
            "access point is missing (might be powered off). The access point "
            "can be specified by the AP name or the AP model"
        ),
        elements=[
            (
                "ap_name",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            TextInput(title=_("AP name")),
                            MonitoringState(title=_("State when missing"), default_value=2),
                        ],
                    ),
                    title=_("Access point name"),
                    add_label=_("Add name"),
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_wlc",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Access Point")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_wlc,
        title=lambda: _("Cisco WLAN AP"),
    )
)
