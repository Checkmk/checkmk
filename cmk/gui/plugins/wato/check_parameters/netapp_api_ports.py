#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, ListChoice


def _valuespec_discovery_netapp_api_ports_ignored():
    return Dictionary(
        title=_("Netapp port discovery"),
        elements=[
            (
                "ignored_ports",
                ListChoice(
                    title=_("Ignore port types during discovery"),
                    help=_("Specify which port types should not be discovered"),
                    choices=[
                        ("physical", _("Physical")),
                        ("vlan", _("Vlan")),
                        ("trunk", _("Trunk")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_netapp_api_ports_ignored",
        valuespec=_valuespec_discovery_netapp_api_ports_ignored,
    )
)
