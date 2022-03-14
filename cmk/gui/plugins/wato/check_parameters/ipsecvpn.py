#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, ListOfStrings, Transform, Tuple


def _parameter_valuespec_ipsecvpn():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Levels for number of down channels"),
                        elements=[
                            Integer(title=_("Warning at"), default_value=1),
                            Integer(title=_("Critical at"), default_value=2),
                        ],
                    ),
                ),
                ("tunnels_ignore_levels", ListOfStrings(title=_("Tunnels which ignore levels"))),
            ],
            optional_keys=[],
        ),
        forth=lambda params: isinstance(params, dict) and params or {"levels": params},
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ipsecvpn",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ipsecvpn,
        title=lambda: _("Fortigate IPSec VPN Tunnels"),
    )
)
