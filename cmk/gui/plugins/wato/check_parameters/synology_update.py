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
from cmk.gui.valuespec import Dictionary, ListChoice

synology_update_states = [
    (1, "Available"),
    (2, "Unavailable"),
    (4, "Disconnected"),
    (5, "Others"),
]


def _parameter_valuespec_synology_update():
    return Dictionary(
        title=_("Update State"),
        elements=[
            (
                "ok_states",
                ListChoice(
                    title=_("States which result in OK"),
                    choices=synology_update_states,
                    default_value=[2],
                ),
            ),
            (
                "warn_states",
                ListChoice(
                    title=_("States which result in Warning"),
                    choices=synology_update_states,
                    default_value=[5],
                ),
            ),
            (
                "crit_states",
                ListChoice(
                    title=_("States which result in Critical"),
                    choices=synology_update_states,
                    default_value=[1, 4],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="synology_update",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_synology_update,
        title=lambda: _("Synology Updates"),
    )
)
