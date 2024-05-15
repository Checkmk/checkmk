#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import TextInput, Tuple
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.watolib.rulespecs import HostRulespec, Rulespec, rulespec_registry


def _factory_default_special_agents_hivemanager():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager():
    return Tuple(
        title=_("Aerohive HiveManager"),
        help=_("Activate monitoring of host via a HTTP connect to the HiveManager"),
        elements=[
            TextInput(title=_("Username")),
            MigrateToIndividualOrStoredPassword(title=_("Password")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager(),
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("hivemanager"),
        valuespec=_valuespec_special_agents_hivemanager,
    )
)
