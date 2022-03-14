#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.ibm_mq_plugin import ibm_mq_version
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOf, MonitoringState, TextInput, Tuple


def _parameter_valuespec_ibm_mq_managers():
    return Dictionary(
        elements=[
            (
                "mapped_states",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                title=_("Queue manager state"),
                                choices=[
                                    ("starting", "STARTING"),
                                    ("running", "RUNNING"),
                                    ("running_as_standby", "RUNNING AS STANDBY"),
                                    ("running_elsewhere", "RUNNING ELSEWHERE"),
                                    ("quiescing", "QUIESCING"),
                                    ("ending_immediately", "ENDING IMMEDIATELY"),
                                    ("ending_pre_emptively", "ENDING PRE-EMPTIVLEY"),
                                    ("ended_normally", "ENDED NORMALLY"),
                                    ("ended_immediately", "ENDED IMMEDIATELY"),
                                    ("ended_unexpectedly", "ENDED UNEXPECTEDLY"),
                                    ("ended_pre_emptively", "ENDED PRE-EMPTIVELY"),
                                    ("status_not_available", "STATUS NOT AVAILABLE"),
                                ],
                            ),
                            MonitoringState(
                                title=_("Service state"),
                            ),
                        ],
                    ),
                    title=_("Map manager state to service state"),
                    help=_(
                        """If you do not use this parameter, the following factory
             defaults apply:<br>
                STARTING: OK<br>
                RUNNING: OK<br>
                RUNNING AS STANDBY: OK<br>
                RUNNING ELSEWHERE: OK<br>
                QUIESCING: OK<br>
                ENDING IMMEDIATELY: OK<br>
                ENDING PRE-EMPTIVELY: OK<br>
                ENDED NORMALLY: OK<br>
                ENDED IMMEDIATELY: OK<br>
                ENDED UNEXPECTEDLY: CRIT<br>
                ENDED PRE-EMPTIVELY: WARN<br>
                STATUS NOT AVAILABLE: OK<br>
             """
                    ),
                ),
            ),
            (
                "mapped_states_default",
                MonitoringState(title=_("Service state if no map rule matches"), default_value=2),
            ),
        ]
        + ibm_mq_version(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_mq_managers",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Name of Queue Manager")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_mq_managers,
        title=lambda: _("IBM MQ Managers"),
    )
)
