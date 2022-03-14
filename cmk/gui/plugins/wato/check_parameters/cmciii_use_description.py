#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice


def _valuespec_discovery_cmciii():
    return Dictionary(
        title=_("Rittal CMC III discovery"),
        elements=[
            (
                "use_sensor_description",
                DropdownChoice(
                    title=_("Service description"),
                    help=_(
                        "Since the sensor description is a user defined text, multiple sensors "
                        "may have the same description. To ensure that items are unique, they "
                        "are prefixed with X-Y where X is the device number and Y the index "
                        "of the sensor."
                    ),
                    choices=[
                        (False, _("Use device and sensor name")),
                        (True, _("Use sensor description")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_cmciii",
        valuespec=_valuespec_discovery_cmciii,
    )
)
