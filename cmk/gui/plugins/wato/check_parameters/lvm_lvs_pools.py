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


def _item_spec_lvm_lvs_pools():
    return TextInput(
        title=_("Logical Volume Pool"),
        allow_empty=True,
    )


def _parameter_valuespec_lvm_lvs_pools():
    return Dictionary(
        elements=[
            (
                "levels_meta",
                Tuple(
                    title=_("Levels for Meta"),
                    default_value=(80.0, 90.0),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%")),
                        Percentage(title=_("Critical at"), unit=_("%")),
                    ],
                ),
            ),
            (
                "levels_data",
                Tuple(
                    title=_("Levels for Data"),
                    default_value=(80.0, 90.0),
                    elements=[
                        Percentage(title=_("Warning at"), unit=_("%")),
                        Percentage(title=_("Critical at"), unit=_("%")),
                    ],
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="lvm_lvs_pools",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_lvm_lvs_pools,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_lvm_lvs_pools,
        title=lambda: _("Logical Volume Pools (LVM)"),
    )
)
