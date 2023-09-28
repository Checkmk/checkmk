#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _parameter_valuespec_wlc_clients() -> Dictionary:
    return Dictionary(
        title=_("Number of connections"),
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Upper levels"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("connections")),
                        Integer(title=_("Critical at"), unit=_("connections")),
                    ],
                ),
            ),
            (
                "levels_lower",
                Tuple(
                    title=_("Lower levels"),
                    elements=[
                        Integer(title=_("Critical if below"), unit=_("connections")),
                        Integer(title=_("Warning if below"), unit=_("connections")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="wlc_clients",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Name of Wifi")),
        parameter_valuespec=_parameter_valuespec_wlc_clients,
        title=lambda: _("WLC WiFi client connections"),
    )
)
