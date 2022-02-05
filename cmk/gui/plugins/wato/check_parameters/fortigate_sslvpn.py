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


def _parameter_valuespec_fortigate_sslvpn():
    return Dictionary(
        elements=[
            (
                "tunnel_levels",
                Tuple(
                    title=_("VPN tunnels"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortigate_sslvpn",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Virtual domain")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortigate_sslvpn,
        title=lambda: _("Fortigate SSL VPN"),
    )
)
