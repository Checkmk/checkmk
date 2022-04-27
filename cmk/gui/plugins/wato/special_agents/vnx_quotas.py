#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Password, TextInput
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_vnx_quotas():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_vnx_quotas():
    return Dictionary(
        title=_("VNX quotas and filesystems"),
        elements=[
            ("user", TextInput(title=_("NAS DB user name"))),
            ("password", Password(title=_("Password"))),
            ("nas_db", TextInput(title=_("NAS DB path"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_vnx_quotas(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:vnx_quotas",
        valuespec=_valuespec_special_agents_vnx_quotas,
    )
)
