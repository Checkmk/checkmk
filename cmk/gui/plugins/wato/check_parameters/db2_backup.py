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
from cmk.gui.valuespec import Age, Dictionary, Migrate, TextInput


def _item_spec_db2_backup():
    return TextInput(
        title=_("Instance"), help=_("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    )


def _parameter_valuespec_db2_backup():
    return Migrate(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    SimpleLevels(
                        title=_("Levels on time since last successful backup"),
                        spec=Age,
                        default_levels=(86400 * 14, 86400 * 28),
                    ),
                ),
            ],
            optional_keys=[],
        ),
        migrate=lambda p: p if isinstance(p, dict) else {"levels": p},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_backup",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_backup,
        parameter_valuespec=_parameter_valuespec_db2_backup,
        title=lambda: _("DB2 Time since last database Backup"),
    )
)
