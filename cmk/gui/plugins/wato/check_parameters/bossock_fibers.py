#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Integer, Migrate, TextInput


def _parameter_valuespec_bossock_fibers():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                ("levels", SimpleLevels(spec=Integer, unit="fibers", title=_("Number of fibers")))
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="bossock_fibers",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(title=_("Node ID")),
        parameter_valuespec=_parameter_valuespec_bossock_fibers,
        title=lambda: _("Number of Running Bossock Fibers"),
    )
)
