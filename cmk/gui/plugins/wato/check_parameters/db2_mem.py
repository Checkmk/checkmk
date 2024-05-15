#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.plugins.wato.utils.simple_levels import SimpleLevels
from cmk.gui.valuespec import Dictionary, Migrate, Percentage, TextInput


def _parameter_valuespec_db2_mem():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels_lower",
                    SimpleLevels(
                        spec=Percentage,
                        # xgettext: no-python-format
                        unit=_("% memory left"),
                        direction="lower",
                    ),
                )
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels_lower": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_mem",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Instance name"), allow_empty=True),
        parameter_valuespec=_parameter_valuespec_db2_mem,
        title=lambda: _("DB2 memory usage"),
    )
)
