#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    HostRulespec,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
    RulespecGroupCheckParametersDiscovery,
)
from cmk.gui.valuespec import Dictionary, FixedValue, ListOf, MonitoringState, TextInput

_STATE = {0: "OK", 1: "WARN", 2: "CRIT"}


def _parameter_valuespec_windows_tasks():
    return Dictionary(
        elements=[
            (
                "exit_code_to_state",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "exit_code",
                                TextInput(
                                    title=_("Exit code (hex value)"),
                                    help=_(
                                        "Enter the exit code as 10-digit, lower case hex value, "
                                        "e.g. 0x00000000."
                                    ),
                                    regex=r"^0x[0-9a-f]{8}$",
                                    regex_error=_(
                                        "Please enter a 10-digit, lower case hex value, e.g. "
                                        "0x00000000 or 0x8004131f."
                                    ),
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
                                TextInput(
                                    title=_("Service output text"),
                                    help=_(
                                        "Display this text in the service output. You can skip "
                                        "this field if you only want to change the monitoring "
                                        "state but not the text produced by the service."
                                    ),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=["info_text"],
                    ),
                    title=_("Map exit code to monitoring state"),
                    help=_(
                        "Specify how Checkmk will translate the exit code of a task into a monitoring state."
                        " This will overwrite the default mapping used by the check plug-in."
                        " You can also decide to only partially overwrite the default mapping by only specifying the new monitoring state."
                        " The default text will be kept as the summary, then.\n\n"
                        " The defaults are shown in the checks man page (see <i>%s</i>)."
                    )
                    % _("Catalog of check plug-ins"),
                ),
            ),
            (
                "state_not_enabled",
                MonitoringState(
                    title=_("Monitoring state if task is not enabled"),
                    help=_(
                        "Set the monitoring state of tasks which are not enabled (for example "
                        "because they were disabled after being discovered)."
                    ),
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="windows_tasks",
        group=RulespecGroupCheckParametersApplications,
        item_spec=lambda: TextInput(title=_("Task name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_windows_tasks,
        title=lambda: _("Windows Tasks"),
    )
)


def _valuespec_windows_tasks_discovery():
    return Dictionary(
        title=_("Windows Tasks"),
        elements=[
            (
                "discover_disabled",
                FixedValue(
                    title=_("Discover disabled tasks"),
                    value=True,
                    totext=_("Tasks are discovered regardless of scheduled task state."),
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupCheckParametersDiscovery,
        match_type="dict",
        name="windows_tasks_discovery",
        valuespec=_valuespec_windows_tasks_discovery,
    )
)
