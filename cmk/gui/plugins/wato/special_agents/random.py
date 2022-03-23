#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsTesting
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import FixedValue


def _factory_default_special_agents_random():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_random():
    return FixedValue(
        value={},
        title=_("Create random monitoring data"),
        help=_(
            "By configuring this rule for a host - instead of the normal "
            "Check_MK agent random monitoring data will be created."
        ),
        totext=_("Create random monitoring data"),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_random(),
        group=RulespecGroupDatasourceProgramsTesting,
        name="special_agents:random",
        valuespec=_valuespec_special_agents_random,
    )
)
