#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.bluecat_ntp import bluecat_operstates
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, ListChoice


def _parameter_valuespec_bluecat_command_server():
    return Dictionary(
        elements=[
            (
                "oper_states",
                Dictionary(
                    title=_("Operations States"),
                    elements=[
                        (
                            "warning",
                            ListChoice(
                                title=_("States treated as warning"),
                                choices=bluecat_operstates,
                                default_value=[2, 3, 4],
                            ),
                        ),
                        (
                            "critical",
                            ListChoice(
                                title=_("States treated as critical"),
                                choices=bluecat_operstates,
                                default_value=[5],
                            ),
                        ),
                    ],
                    required_keys=["warning", "critical"],
                ),
            ),
        ],
        required_keys=["oper_states"],  # There is only one value, so its required
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="bluecat_command_server",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_bluecat_command_server,
        title=lambda: _("Bluecat Command Server Settings"),
    )
)
