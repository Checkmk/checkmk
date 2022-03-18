#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, Password, TextInput


def _valuespec_special_agents_ddn_s2a():
    return Dictionary(
        elements=[
            ("username", TextInput(title=_("Username"), allow_empty=False)),
            ("password", Password(title=_("Password"), allow_empty=False)),
            ("port", Integer(title=_("Port"), default_value=8008)),
        ],
        optional_keys=["port"],
        title=_("DDN S2A"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:ddn_s2a",
        valuespec=_valuespec_special_agents_ddn_s2a,
    )
)
