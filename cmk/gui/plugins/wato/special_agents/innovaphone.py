#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    connection_set,
    RulespecGroupDatasourceProgramsHardware,
)
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Transform
from cmk.gui.watolib.rulespecs import Rulespec


def _factory_default_special_agents_innovaphone():
    # No default, do not use setting if no rule matches
    return Rulespec.FACTORY_DEFAULT_UNUSED


def special_agents_innovaphone_transform(value):
    if isinstance(value, tuple):
        return {
            "auth_basic": {
                "username": value[0],
                "password": ("password", value[1]),
            },
        }
    return value


def _valuespec_special_agents_innovaphone():
    return Transform(
        valuespec=Dictionary(
            title=_("Innovaphone Gateways"),
            help=_("Please specify the user and password needed to access the xml interface"),
            elements=connection_set(
                options=["protocol", "ssl_verify"],
                auth_option="basic",
            ),
            optional_keys=["protocol", "no-cert-check"],
        ),
        forth=special_agents_innovaphone_transform,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_innovaphone(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:innovaphone",
        valuespec=_valuespec_special_agents_innovaphone,
    )
)
