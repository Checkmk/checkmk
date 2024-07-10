#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary, TextInput
from cmk.gui.wato import (
    MigrateToIndividualOrStoredPassword,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_special_agents_vnx_quotas():
    return Dictionary(
        title=_("VNX quotas and filesystems"),
        elements=[
            ("user", TextInput(title=_("NAS DB user name"))),
            ("password", MigrateToIndividualOrStoredPassword(title=_("Password"))),
            ("nas_db", TextInput(title=_("NAS DB path"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name=RuleGroup.SpecialAgents("vnx_quotas"),
        valuespec=_valuespec_special_agents_vnx_quotas,
    )
)
