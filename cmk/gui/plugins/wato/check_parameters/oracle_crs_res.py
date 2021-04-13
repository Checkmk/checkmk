#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Age,
    Dictionary,
    TextAscii,
    Tuple,
    Integer,
    DropdownChoice
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersStorage,
    CheckParameterRulespecWithItem,
    rulespec_registry,
    HostRulespec,
)


def _item_spec_oracle_crs_res():
    return TextAscii(
        title=_("Queue Name"),
        help=_("The name of the queue like in the Apache queue manager")
    )


def _parameter_valuespec_orcale_crs_res():
    return Dictionary(
        elements=[
            ("restarget",
                DropdownChoice(
                    title=_("Override target state"),
                    choices=[
                        ('online', 'ONLINE'),
                        ('intermediate', 'INTERMEDIATE')
                    ]
                )
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="orcale_crs_res",
        item_spec=_item_spec_oracle_crs_res,
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_orcale_crs_res,
        title=lambda: _("Oracle CRS Resource"),
    ))
