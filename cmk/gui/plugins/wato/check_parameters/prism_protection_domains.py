#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersVirtualization,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput


def _parameter_valuespec_prism_protection_domains():
    return Dictionary(
        elements=[
            (
                "sync_state",
                DropdownChoice(
                    title=_("Target sync state"),
                    help=_("Configure the target state of the protection domain sync state."),
                    choices=[
                        ("Enabled", "Sync enabled"),
                        ("Disabled", "Symc disabled"),
                        ("Synchronizing", "Syncing"),
                    ],
                    default_value=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prism_protection_domains",
        item_spec=lambda: TextInput(title=_("Protection Domain")),
        group=RulespecGroupCheckParametersVirtualization,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prism_protection_domains,
        title=lambda: _("Nutanix Prism MetroAvail Sync State"),
    )
)
