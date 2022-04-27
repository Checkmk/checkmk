#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsApps
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, DropdownChoice, TextInput
from cmk.gui.watolib.rulespecs import Rulespec


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
                TextInput(
                    title=_("Password"),
                    allow_empty=False,
                ),
            ),
        ],
        required_keys=["username", "password"],
        title=_("Zerto"),
        help=_("This rule selects the Zerto special agent for an existing Checkmk host"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:zerto",
        valuespec=_valuespec_special_agents_zerto,
    )
)
