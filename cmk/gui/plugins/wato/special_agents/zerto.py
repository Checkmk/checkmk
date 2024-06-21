#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput
from cmk.gui.wato import MigrateToIndividualOrStoredPassword, RulespecGroupDatasourceProgramsApps
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec, rulespec_registry


def _factory_default_special_agents_zerto():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_zerto():
    return Dictionary(
        elements=[
            (
                "authentication",
                DropdownChoice(
                    title=_("Authentication method"),
                    choices=[
                        ("windows", _("Windows authentication")),
                        ("vcenter", _("VCenter authentication")),
                    ],
                    help=_("Default is Windows authentication"),
                ),
            ),
            ("username", TextInput(title=_("Username"), allow_empty=False)),
            (
                "password",
                MigrateToIndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
        ],
        required_keys=["username", "password"],
        title=_("Zerto"),
        help=_(
            "Monitor if your VMs are properly protected by the "
            "disaster recovery software Zerto (compatible with Zerto v9.x)."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name=RuleGroup.SpecialAgents("zerto"),
        valuespec=_valuespec_special_agents_zerto,
    )
)
