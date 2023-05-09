#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    ListOf,
    MonitoringState,
    TextAscii,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_websphere_mq_instance():
    return Dictionary(elements=[
        ("map_instance_states",
         ListOf(
             Tuple(
                 orientation="horizontal",
                 elements=[
                     DropdownChoice(choices=[
                         ('active', _('Active')),
                         ('standby', _('Standby')),
                     ],),
                     MonitoringState(),
                 ],
             ),
             title=_('Map instance state'),
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="websphere_mq_instance",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of manager or instance")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_websphere_mq_instance,
        title=lambda: _("Websphere MQ Instance"),
    ))
