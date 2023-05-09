#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    MonitoringState,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)


def _parameter_valuespec_cisco_asa_failover():
    return Dictionary(elements=[
        ("primary",
         DropdownChoice(
             title=_("Primary Device"),
             help=_("The role of the primary device"),
             choices=[
                 ("active", _("Active unit")),
                 ("standby", _("Standby unit")),
             ],
             default_value="active",
         )),
        ("secondary",
         DropdownChoice(
             title=_("Secondary Device"),
             help=_("The role of the secondary device"),
             choices=[
                 ("active", _("Active unit")),
                 ("standby", _("Standby unit")),
             ],
             default_value="standby",
         )),
        ("failover_state",
         MonitoringState(
             title=_("Failover state"),
             help=_("State if conditions above are not satisfied"),
             default_value=0,
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="cisco_asa_failover",
        group=RulespecGroupCheckParametersNetworking,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_cisco_asa_failover,
        title=lambda: _("Failover states"),
    ))
