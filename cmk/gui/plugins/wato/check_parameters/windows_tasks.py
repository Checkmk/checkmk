#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    ListOf,
    MonitoringState,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)


def _parameter_valuespec_windows_tasks():
    return Dictionary(elements=[
        (
            "exit_code_to_state",
            ListOf(
                Dictionary(
                    elements=[
                        (
                            "exit_code",
                            TextAscii(
                                title=_("Exit code (hex value)"),
                                help=_("Enter the exit code as 10-digit, lower case hex value, "
                                       "e.g. 0x00000000."),
                                regex=r"^0x[0-9a-f]{8}$",
                                regex_error=_("Please enter a 10-digit, lower case hex value, e.g. "
                                              "0x00000000 or 0x8004131f."),
                            ),
                        ),
                        (
                            "monitoring_state",
                            MonitoringState(
                                title=_("Monitoring state"),
                                default_value=0,
                            ),
                        ),
                        (
                            "info_text",
                            TextAscii(
                                title=_("Service output text"),
                                help=_("Display this text in the service output. You can skip "
                                       "this field if you only want to change the monitoring "
                                       "state but not the text produced by the service."),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=["info_text"],
                ),
                title=_("Map exit code to monitoring state"),
                help=_("Here, you can specify how Checkmk will translate the exit code of a "
                       "task into a monitoring state. This will overwrite the default mapping "
                       "used by the check plugin."),
            ),
        ),
        (
            "state_not_enabled",
            MonitoringState(
                title=_("Monitoring state if task is not enabled"),
                help=_("Set the monitoring state of tasks which are not enabled (for example "
                       "because they were disabled after being discovered)."),
            ),
        ),
    ],)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="windows_tasks",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextAscii(title=_("Task name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_windows_tasks,
        title=lambda: _("Windows Tasks"),
    ))
