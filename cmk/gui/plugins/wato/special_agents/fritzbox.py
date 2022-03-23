#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer


def _factory_default_special_agents_fritzbox():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_fritzbox():
    return Dictionary(
        title=_("Fritz!Box Devices"),
        help=_(
            "This rule selects the Fritz!Box agent, which uses UPNP to gather information "
            "about configuration and connection status information."
        ),
        elements=[
            (
                "timeout",
                Integer(
                    title=_("Connect Timeout"),
                    help=_(
                        "The network timeout in seconds when communicating via UPNP. "
                        "The default is 10 seconds. Please note that this "
                        "is not a total timeout, instead it is applied to each API call."
                    ),
                    default_value=10,
                    minvalue=1,
                    unit=_("seconds"),
                ),
            ),
        ],
        optional_keys=["timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_fritzbox(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:fritzbox",
        valuespec=_valuespec_special_agents_fritzbox,
    )
)
