#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<windows_tasks:sep(58)>>>
# TaskName             : \WebShopPictureUpload
# Last Run Time        : 17.10.2013 23:00:00
# Next Run Time        : 18.10.2013 23:00:00
# Last Result          : 0
# Scheduled Task State : Enabled
#
# TaskName             : \OfficeSoftwareProtectionPlatform\SvcRestartTask
# Last Run Time        : N/A
# Next Run Time        : Disabled
# Last Result          : 1
# Scheduled Task State : Disabled

# A list of all task state can be found here:
# http://msdn.microsoft.com/en-us/library/aa383604%28VS.85%29.aspx

from typing import Literal, NotRequired, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def parse_windows_tasks(string_table: StringTable) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    last_task: str | None = None
    for line in string_table:
        name = line[0].strip()
        value = ":".join(line[1:]).strip()
        if value and last_task and name != "TaskName":
            data[last_task][name] = value

        elif name == "TaskName":
            last_task = value
            data[last_task] = {}

        # this is a line continuation from TaskName
        elif last_task is not None and not value and not data[last_task]:
            data.pop(last_task)
            last_task += " " + name
            data[last_task] = {}

    return data


agent_section_windows_tasks = AgentSection(
    name="windows_tasks",
    parse_function=parse_windows_tasks,
)


class DiscoveryParams(TypedDict):
    discover_disabled: NotRequired[Literal[True]]


def discovery_windows_tasks(
    params: DiscoveryParams, section: dict[str, dict[str, str]]
) -> DiscoveryResult:
    discover_disabled = params.get("discover_disabled", False)
    for n, v in section.items():
        if discover_disabled or v.get("Scheduled Task State") != "Disabled":
            yield Service(item=n)


# Code duplication with cmk/gui/plugins/wato/check_parameters/windows_tasks.py
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


class ExitCodeToState(TypedDict):
    exit_code: str
    monitoring_state: Literal[0, 1, 2, 3]
    info_text: NotRequired[str]


class Params(TypedDict):
    exit_code_to_state: NotRequired[list[ExitCodeToState]]
    state_not_enabled: NotRequired[Literal[0, 1, 2, 3]]


def check_windows_tasks(
    item: str, params: Params, section: dict[str, dict[str, str]]
) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary="Task not found on server")
        return

    state_not_enabled = params.get("state_not_enabled", 1)

    custom_map_exit_codes: dict[str, tuple[Literal[0, 1, 2, 3], str]] = {
        user_defined_mapping["exit_code"]: (
            user_defined_mapping["monitoring_state"],
            user_defined_mapping.get(
                "info_text",
                # in case info_text was not specified, we use the default one if available
                _MAP_EXIT_CODES.get(user_defined_mapping["exit_code"], (0, ""))[1],
            ),
        )
        for user_defined_mapping in params.get("exit_code_to_state", [])
    }
    map_exit_codes = {
        **_MAP_EXIT_CODES,
        **custom_map_exit_codes,
    }

    data = section[item]
    last_result = data["Last Result"]

    # schtasks.exe (used by the check plug-in) returns a signed integer
    # e.g. -2147024629. However, error codes are unsigned integers.
    # To make it easier for the user to lookup the error code (e.g. on
    # MSDN) we convert the negative numbers to the hexadecimal
    # representation.
    last_result_unsigned = int(last_result) & 0xFFFFFFFF
    last_result_hex = f"{last_result_unsigned:#010x}"  # padding with zeros

    state, state_txt = map_exit_codes.get(
        last_result_hex,
        (2, None),
    )
    yield Result(
        state=State(state),
        summary=(
            f"{state_txt} ({last_result_hex})" if state_txt else f"Got exit code {last_result_hex}"
        ),
    )

    if data.get("Scheduled Task State", None) != "Enabled":
        yield Result(state=State(state_not_enabled), summary="Task not enabled")

    additional_infos = []
    for key, title in [
        ("Last Run Time", "Last run time"),
        ("Next Run Time", "Next run time"),
    ]:
        if key in data:
            additional_infos.append(f"{title}: {data[key]}")

    if additional_infos:
        yield Result(state=State.OK, summary=", ".join(additional_infos))


check_plugin_windows_tasks = CheckPlugin(
    name="windows_tasks",
    check_function=check_windows_tasks,
    check_ruleset_name="windows_tasks",
    discovery_function=discovery_windows_tasks,
    discovery_default_parameters={},
    discovery_ruleset_name="windows_tasks_discovery",
    service_name="Task %s",
    check_default_parameters={
        # This list is overruled by a ruleset, if configured.
        # The defaults are brought back individually below.
        # Put them here anyway to make them available in the checks man page.
        "exit_code_to_state": [
            {
                "exit_code": key,
                "monitoring_state": state,
                "info_text": text,
            }
            for key, (state, text) in _MAP_EXIT_CODES.items()
        ],
    },
)
