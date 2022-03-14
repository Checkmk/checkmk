#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput


def _parameter_valuespec_hacmp_resources() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "expect_online_on",
                DropdownChoice(
                    title=_("Expect resource to be online on"),
                    choices=[
                        ("first", _("the first node")),
                        ("any", _("any node")),
                    ],
                ),
            ),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="hacmp_resources",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Resource Group")),
        parameter_valuespec=_parameter_valuespec_hacmp_resources,
        title=lambda: _("AIX HACMP Resource Groups"),
    )
)
