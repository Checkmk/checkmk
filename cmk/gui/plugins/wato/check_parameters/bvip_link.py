#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, ListChoice

bvip_link_states = [
    (0, "No Link"),
    (1, "10 MBit - HalfDuplex"),
    (2, "10 MBit - FullDuplex"),
    (3, "100 Mbit - HalfDuplex"),
    (4, "100 Mbit - FullDuplex"),
    (5, "1 Gbit - FullDuplex"),
    (7, "Wifi"),
]


def _parameter_valuespec_bvip_link():
    return Dictionary(
        title=_("Update State"),
        elements=[
            (
                "ok_states",
                ListChoice(
                    title=_("States which result in OK"),
                    choices=bvip_link_states,
                    default_value=[0, 4, 5],
                ),
            ),
            (
                "warn_states",
                ListChoice(
                    title=_("States which result in Warning"),
                    choices=bvip_link_states,
                    default_value=[7],
                ),
            ),
            (
                "crit_states",
                ListChoice(
                    title=_("States which result in Critical"),
                    choices=bvip_link_states,
                    default_value=[1, 2, 3],
                ),
            ),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="bvip_link",
        group=RulespecGroupCheckParametersEnvironment,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_bvip_link,
        title=lambda: _("Allowed Network states on Bosch IP Cameras"),
    )
)
