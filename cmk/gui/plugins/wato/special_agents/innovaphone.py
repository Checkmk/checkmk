#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    connection_set,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_innovaphone():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_innovaphone() -> Dictionary:
    return Dictionary(
        title=_("Innovaphone Gateways"),
        help=_("Please specify the user and password needed to access the xml interface"),
        elements=connection_set(
            options=["protocol", "ssl_verify"],
            auth_option="basic",
        ),
        optional_keys=["protocol", "no-cert-check"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_innovaphone(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:innovaphone",
        valuespec=_valuespec_special_agents_innovaphone,
    )
)
