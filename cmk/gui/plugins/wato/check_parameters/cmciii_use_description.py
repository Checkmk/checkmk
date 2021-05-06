#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
)

from cmk.gui.plugins.wato import (
    rulespec_registry,
    RulespecGroupCheckParametersDiscovery,
    HostRulespec,
)


def _valuespec_discovery_cmciii():
    return Dictionary(
        title=_("Rittal CMC III discovery"),
        elements=[
            ("use_sensor_description",
             DropdownChoice(
                 title=_("Service description"),
                 help=_("The sensor description is a user defined text. If you use "
                        "this option, you must ensure that all sensors have a "
                        "unique description. Otherwise two or more sensors can be "
                        "aliased to the same service."),
                 choices=[
                     (False, _("Use device and sensor name")),
                     (True, _("Use sensor description (see help text)")),
                 ],
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="discovery_cmciii",
        valuespec=_valuespec_discovery_cmciii,
    ))
