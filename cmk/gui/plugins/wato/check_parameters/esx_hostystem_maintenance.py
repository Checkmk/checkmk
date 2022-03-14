#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameter_valuespec_esx_hostystem_maintenance():
    return Dictionary(
        elements=[
            (
                "target_state",
                DropdownChoice(
                    title=_("Target State"),
                    help=_("Configure the target mode for the system."),
                    choices=[
                        ("true", "System should be in Maintenance Mode"),
                        ("false", "System not should be in Maintenance Mode"),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="esx_hostystem_maintenance",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_esx_hostystem_maintenance,
        title=lambda: _("ESX Hostsystem Maintenance Mode"),
    )
)
