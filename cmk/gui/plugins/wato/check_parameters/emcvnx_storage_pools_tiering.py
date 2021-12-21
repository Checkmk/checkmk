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
from cmk.gui.valuespec import Age, Dictionary, TextInput, Tuple


def _parameter_valuespec_emcvnx_storage_pools_tiering():
    return Dictionary(
        elements=[
            (
                "time_to_complete",
                Tuple(
                    title=_("Upper levels for estimated time to complete"),
                    elements=[
                        Age(title=_("Warning at"), default_value=300 * 60 * 60),
                        Age(title=_("Critical at"), default_value=350 * 60 * 60),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="emcvnx_storage_pools_tiering",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Pool name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_emcvnx_storage_pools_tiering,
        title=lambda: _("EMC VNX storage pools tiering"),
    )
)
