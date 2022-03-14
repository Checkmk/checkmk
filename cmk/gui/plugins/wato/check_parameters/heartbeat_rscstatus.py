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


def _parameter_valuespec_heartbeat_rscstatus():
    return Dictionary(
        elements=[
            (
                "expected_state",
                DropdownChoice(
                    title=_("Expected state"),
                    choices=[
                        ("none", _("All resource groups are running on a different node (none)")),
                        ("all", _("All resource groups run on this node (all)")),
                        (
                            "local",
                            _(
                                "All resource groups that belong to this node run on this node (local)"
                            ),
                        ),
                        (
                            "foreign",
                            _(
                                "All resource groups are running that are supposed to be running on the other node (foreign)"
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="heartbeat_rscstatus",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_heartbeat_rscstatus,
        title=lambda: _("Heartbeat Ressource Status"),
    )
)
