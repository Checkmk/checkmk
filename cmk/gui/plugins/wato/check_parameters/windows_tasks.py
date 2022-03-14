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
from cmk.gui.valuespec import Dictionary, ListOf, MonitoringState, TextInput

# Code duplication with checks/windows_tasks
# because of base/gui import restrictions
# This is protected via unit test
_MAP_EXIT_CODES = {
    "0x00000000": (0, "The task exited successfully"),
    "0x00041300": (0, "The task is ready to run at its next scheduled time."),
    "0x00041301": (0, "The task is currently running."),
    "0x00041302": (0, "The task will not run at the scheduled times because it has been disabled."),
    "0x00041303": (0, "The task has not yet run."),
    "0x00041304": (0, "There are no more runs scheduled for this task."),
    "0x00041305": (
        1,
        "One or more of the properties that are needed to run this task on a schedule have not been set.",
    ),
    "0x00041306": (0, "The last run of the task was terminated by the user."),
    "0x00041307": (
        1,
        "Either the task has no triggers or the existing triggers are disabled or not set.",
    ),
    "0x00041308": (1, "Event triggers do not have set run times."),
    "0x80041309": (1, "A task's trigger is not found."),
    "0x8004130a": (1, "One or more of the properties required to run this task have not been set."),
    "0x8004130b": (0, "There is no running instance of the task."),
    "0x8004130c": (2, "The Task Scheduler service is not installed on this computer."),
    "0x8004130d": (1, "The task object could not be opened."),
    "0x8004130e": (1, "The object is either an invalid task object or is not a task object."),
    "0x8004130f": (
        1,
        "No account information could be found in the Task Scheduler security database for the task indicated.",
    ),
    "0x80041310": (1, "Unable to establish existence of the account specified."),
    "0x80041311": (
        2,
        "Corruption was detected in the Task Scheduler security database; the database has been reset.",
    ),
    "0x80041312": (1, "Task Scheduler security services are available only on Windows NT."),
    "0x80041313": (1, "The task object version is either unsupported or invalid."),
    "0x80041314": (
        1,
        "The task has been configured with an unsupported combination of account settings and run time options.",
    ),
    "0x80041315": (1, "The Task Scheduler Service is not running."),
    "0x80041316": (1, "The task XML contains an unexpected node."),
    "0x80041317": (
        1,
        "The task XML contains an element or attribute from an unexpected namespace.",
    ),
    "0x80041318": (
        1,
        "The task XML contains a value which is incorrectly formatted or out of range.",
    ),
    "0x80041319": (1, "The task XML is missing a required element or attribute."),
    "0x8004131a": (1, "The task XML is malformed."),
    "0x0004131b": (
        1,
        "The task is registered, but not all specified triggers will start the task.",
    ),
    "0x0004131c": (
        1,
        "The task is registered, but may fail to start. Batch logon privilege needs to be enabled for the task principal.",
    ),
    "0x8004131d": (1, "The task XML contains too many nodes of the same type."),
    "0x8004131e": (1, "The task cannot be started after the trigger end boundary."),
    "0x8004131f": (0, "An instance of this task is already running."),
    "0x80041320": (1, "The task will not run because the user is not logged on."),
    "0x80041321": (1, "The task image is corrupt or has been tampered with."),
    "0x80041322": (1, "The Task Scheduler service is not available."),
    "0x80041323": (
        1,
        "The Task Scheduler service is too busy to handle your request. Please try again later.",
    ),
    "0x80041324": (
        1,
        "The Task Scheduler service attempted to run the task, but the task did not run due to one of the constraints in the task definition.",
    ),
    "0x00041325": (0, "The Task Scheduler service has asked the task to run."),
    "0x80041326": (0, "The task is disabled."),
    "0x80041327": (
        1,
        "The task has properties that are not compatible with earlier versions of Windows.",
    ),
    "0x80041328": (1, "The task settings do not allow the task to start on demand."),
}

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
                        "Here, you can specify how Checkmk will translate the exit code of a "
                        "task into a monitoring state. This will overwrite the default mapping "
                        "used by the check plugin. You can also decide to only partially overwrite "
                        "the default mapping by only specifying the new monitoring state. "
                        "The default text will be kept as the summary, then.<br><br>"
                        "The following exit codes/monitoring states/summaries are specified as default:<br>%s"
                    )
                    % "<br>".join(
                        [
                            f"{exit_code}: {_STATE[matching[0]]} - {matching[1]}"
                            for exit_code, matching in _MAP_EXIT_CODES.items()
                        ]
                    ),
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
