#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Percentage,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.check_parameters.utils import vs_filesystem


def _parameter_valuespec_threepar_capacity():
    return vs_filesystem([
        (
            "failed_capacity_levels",
            Tuple(
                title=_("Levels for failed capacity in percent"),
                elements=[
                    Percentage(title=_("Warning at"), default_value=0.0),
                    Percentage(title=_("Critical at"), default_value=0.0),
                ],
            ),
        ),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="threepar_capacity",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Device type"), allow_empty=False),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_threepar_capacity,
        title=lambda: _("3PAR Capacity (used space and growth)"),
    ))
