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


def _item_spec_pfm_health():
    return TextInput(
        title=_("Number or ID of the disk"),
        help=_(
            "How the disks are named depends on the type of hardware being "
            "used. Please look at already discovered checks for examples."
        ),
    )


def _parameter_valuespec_pfm_health():
    return Dictionary(
        elements=[
            (
                "health_lifetime_perc",
                Tuple(
                    title=_("Lower levels for health lifetime"),
                    elements=[
                        Percentage(title=_("Warning if below"), default_value=10),
                        Percentage(title=_("Critical if below"), default_value=5),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="pfm_health",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_pfm_health,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_pfm_health,
        title=lambda: _("PCIe flash module"),
    )
)
