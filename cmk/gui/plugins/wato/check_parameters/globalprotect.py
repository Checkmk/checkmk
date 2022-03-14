#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    Levels,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary


def _parameter_valuespec_globalprotect_utilization():
    return Dictionary(
        elements=[
            (
                "utilization",
                Levels(
                    title=_("Utilization"),
                    unit=_("%"),
                    default_value=None,
                    default_levels=(80.0, 90.0),
                ),
            ),
            (
                "active_tunnels",
                Levels(
                    title=_("Number of active tunnels"),
                    default_value=None,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="globalprotect_utilization",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_globalprotect_utilization,
        title=lambda: _("GlobalProtect Utilization"),
    )
)
