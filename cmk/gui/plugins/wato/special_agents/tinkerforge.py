#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import RulespecGroupDatasourceProgramsHardware
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import Dictionary, Integer, TextInput


def _valuespec_special_agents_tinkerforge():
    return Dictionary(
        title=_("Tinkerforge"),
        elements=[
            (
                "port",
                Integer(
                    title=_("TCP port number"),
                    help=_("Port number that AppDynamics is listening on. The default is 8090."),
                    default_value=4223,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "segment_display_uid",
                TextInput(
                    title=_("7-segment display uid"),
                    help=_(
                        "This is the uid of the sensor you want to display in the 7-segment display, "
                        "not the uid of the display itself. There is currently no support for "
                        "controling multiple displays."
                    ),
                ),
            ),
            (
                "segment_display_brightness",
                Integer(title=_("7-segment display brightness"), minvalue=0, maxvalue=7),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:tinkerforge",
        valuespec=_valuespec_special_agents_tinkerforge,
    )
)
