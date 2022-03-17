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
from cmk.gui.valuespec import Dictionary, DropdownChoice, MonitoringState, TextInput


def _parameter_valuespec_bonding():
    return Dictionary(
        elements=[
            (
                "expect_active",
                DropdownChoice(
                    title=_("Warn on unexpected active interface"),
                    choices=[
                        ("ignore", _("ignore which one is active")),
                        ("primary", _("require primary interface to be active")),
                        ("lowest", _("require interface that sorts lowest alphabetically")),
                    ],
                    default_value="ignore",
                ),
            ),
            (
                "ieee_302_3ad_agg_id_missmatch_state",
                MonitoringState(
                    title=_("State for mismatching Aggregator IDs for LACP"),
                    default_value=1,
                ),
            ),
        ],
        ignored_keys=["primary"],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="bonding",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=lambda: TextInput(title=_("Name of the bonding interface")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_bonding,
        title=lambda: _("Linux bonding interface status"),
    )
)
