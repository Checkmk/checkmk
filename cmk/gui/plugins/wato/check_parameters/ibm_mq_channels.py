#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOf, MonitoringState, TextInput, Tuple


def _parameter_valuespec_ibm_mq_channels():
    return Dictionary(
        elements=[
            (
                "mapped_states",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("Channel state"),
                                choices=[
                                    ("inactive", "INACTIVE"),
                                    ("initializing", "INITIALIZING"),
                                    ("binding", "BINDING"),
                                    ("starting", "STARTING"),
                                    ("running", "RUNNING"),
                                    ("retrying", "RETRYING"),
                                    ("stopping", "STOPPING"),
                                    ("stopped", "STOPPED"),
                                ],
                            ),
                            MonitoringState(
                                title=_("Service state"),
                            ),
                        ],
                    ),
                    title=_("Map channel state to service state"),
                    help=_(
                        """If you do not use this parameter, the following factory
             defaults apply:<br>
                INACTIVE: OK<br>
                INITIALIZING: OK<br>
                BINDING: OK<br>
                STARTING: OK<br>
                RUNNING: OK<br>
                RETRYING: WARN<br>
                STOPPING: OK<br>
                STOPPED: CRIT<br>
             """
                    ),
                ),
            ),
            (
                "mapped_states_default",
                MonitoringState(title=_("Service state if no map rule matches"), default_value=2),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_mq_channels",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of Channel")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_mq_channels,
        title=lambda: _("IBM MQ Channels"),
    )
)
