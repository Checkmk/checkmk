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
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _item_spec_openhardwaremonitor_smart():
    return TextInput(
        title=_("Device Name"),
        help=_("Name of the Hard Disk as reported by OHM: hdd0, hdd1, ..."),
    )


def _parameter_valuespec_openhardwaremonitor_smart():
    return Dictionary(
        elements=[
            (
                "remaining_life",
                Tuple(
                    title=_("Remaining Life"),
                    help=_("Estimated remaining health of the disk based on other readings."),
                    elements=[
                        Percentage(title=_("Warning below"), default_value=30),
                        Percentage(title=_("Critical below"), default_value=10),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="openhardwaremonitor_smart",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_openhardwaremonitor_smart,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_openhardwaremonitor_smart,
        title=lambda: _("OpenHardwareMonitor S.M.A.R.T."),
    )
)
