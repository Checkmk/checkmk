#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersEnvironment,
)
from cmk.gui.valuespec import Dictionary, Percentage, TextInput, Tuple


def _parameter_valuespec_memory_utilization_multiitem():
    return Dictionary(
        help=_(
            "The memory utilization of components of a device (e.g. memory utilization"
            "of the rack units as components of a rack server as device) in the last"
            "check interval. The possible range is from 0% to 100%"
        ),
        elements=[
            (
                "upper_levels",
                Tuple(
                    title=_("Alert on too high memory utilization"),
                    elements=[
                        Percentage(title=_("Warning at"), default_value=90.0),
                        Percentage(title=_("Critical at"), default_value=95.0),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="memory_utilization_multiitem",
        group=RulespecGroupCheckParametersEnvironment,
        item_spec=lambda: TextInput(title=_("Component"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_utilization_multiitem,
        title=lambda: _("Device Component Memory Utilization"),
    )
)
