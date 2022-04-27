#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Password, TextInput, Tuple
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_hivemanager():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager():
    return Tuple(
        title=_("Aerohive HiveManager"),
        help=_("Activate monitoring of host via a HTTP connect to the HiveManager"),
        elements=[
            TextInput(title=_("Username")),
            Password(title=_("Password")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:hivemanager",
        valuespec=_valuespec_special_agents_hivemanager,
    )
)
