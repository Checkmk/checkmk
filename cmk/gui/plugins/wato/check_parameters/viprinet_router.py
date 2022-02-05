#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _parameter_valuespec_viprinet_router():
    return Dictionary(
        elements=[
            (
                "expect_mode",
                DropdownChoice(
                    title=_("Set expected router mode"),
                    choices=[
                        ("inv", _("Mode found during inventory")),
                        ("0", _("Node")),
                        ("1", _("Hub")),
                        ("2", _("Hub running as HotSpare")),
                        ("3", _("Hotspare-Hub replacing another router")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="viprinet_router",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_viprinet_router,
        title=lambda: _("Viprinet router"),
    )
)
