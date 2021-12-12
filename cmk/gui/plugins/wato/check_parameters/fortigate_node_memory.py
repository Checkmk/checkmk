#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _parameter_valuespec_fortigate_node_memory():
    return Dictionary(
        elements=[
            (
                "levels",
                Tuple(
                    title=_("Levels"),
                    elements=[
                        Percentage(
                            title=_("Warning at"),
                            default_value=70.0,
                        ),
                        Percentage(
                            title=_("Critical at"),
                            default_value=80.0,
                        ),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="fortigate_node_memory",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(
            title=_("node"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_fortigate_node_memory,
        title=lambda: _("Fortigate node memory"),
    )
)
