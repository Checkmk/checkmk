#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


def _parameter_valuespec_msx_rpcclientaccess():
    return Dictionary(
        title=_("Set Levels"),
        elements=[
            (
                "latency",
                Tuple(
                    title=_("Average latency for RPC requests"),
                    elements=[
                        Float(title=_("Warning at"), unit=_("ms"), default_value=200.0),
                        Float(title=_("Critical at"), unit=_("ms"), default_value=250.0),
                    ],
                ),
            ),
            (
                "requests",
                Tuple(
                    title=_("Maximum number of RPC requests per second"),
                    elements=[
                        Integer(title=_("Warning at"), unit=_("requests"), default_value=30),
                        Integer(title=_("Critical at"), unit=_("requests"), default_value=40),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="msx_rpcclientaccess",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_rpcclientaccess,
        title=lambda: _("MS Exchange RPC Client Access"),
    )
)
