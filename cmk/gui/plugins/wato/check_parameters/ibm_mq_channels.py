#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    MonitoringState,
    TextAscii,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_ibm_mq_channels():
    return Dictionary(elements=[
        ("status",
         Dictionary(
             title=_('Override check state based on channel state'),
             elements=[
                 ("INACTIVE", MonitoringState(title=_("When INACTIVE"), default_value=0)),
                 ("INITIALIZING", MonitoringState(title=_("When INITIALIZING"), default_value=0)),
                 ("BINDING", MonitoringState(title=_("When BINDING"), default_value=0)),
                 ("STARTING", MonitoringState(title=_("When STARTING"), default_value=0)),
                 ("RUNNING", MonitoringState(title=_("When RUNNING"), default_value=0)),
                 ("RETRYING", MonitoringState(title=_("When RETRYING"), default_value=1)),
                 ("STOPPING", MonitoringState(title=_("When STOPPING"), default_value=0)),
                 ("STOPPED", MonitoringState(title=_("When STOPPED"), default_value=2)),
                 ("other",
                  MonitoringState(title=_("State when channel status is unknown"),
                                  default_value=2)),
             ],
             optional_keys=[],
         )),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_mq_channels",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Name of Channel")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_mq_channels,
        title=lambda: _("IBM MQ Channels"),
    ))
