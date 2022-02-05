#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, MonitoringState, Percentage, TextInput, Tuple


def _parameter_valuespec_netapp_snapshots():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels for used configured reserve"),
                    elements=[
                        Percentage(title=_("Warning at or above"), unit="%", default_value=85.0),
                        Percentage(title=_("Critical at or above"), unit="%", default_value=90.0),
                    ],
                ),
            ),
            (
                "state_noreserve",
                MonitoringState(
                    title=_("State if no reserve is configured"),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_snapshots",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Volume name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_snapshots,
        title=lambda: _("NetApp Snapshot Reserve"),
    )
)
