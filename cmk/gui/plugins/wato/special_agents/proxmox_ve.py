#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupVMCloudContainer
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import Dictionary, FixedValue, Integer, TextInput


def _valuespec_special_agents_proxmox_ve():
    return Dictionary(
        elements=[
            ("username", TextInput(title=_("Username"), allow_empty=False)),
            ("password", IndividualOrStoredPassword(title=_("Password"), allow_empty=False)),
            ("port", Integer(title=_("Port"), default_value=8006)),
            (
                "no-cert-check",
                FixedValue(
                    value=True,
                    title=_("Disable SSL certificate validation"),
                    totext=_("SSL certificate validation is disabled"),
                ),
            ),
            (
                "timeout",
                Integer(
                    title=_("Query Timeout"),
                    help=_("The network timeout in seconds"),
                    default_value=50,
                    minvalue=1,
                    unit=_("seconds"),
                ),
            ),
            (
                "log-cutoff-weeks",
                Integer(
                    title=_("Maximum log age"),
                    help=_("Age in weeks of log data to fetch"),
                    default_value=2,
                    unit=_("weeks"),
                ),
            ),
        ],
        title=_("Proxmox VE"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:proxmox_ve",
        valuespec=_valuespec_special_agents_proxmox_ve,
    )
)
