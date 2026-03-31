#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

from cmk.gui.agent_bakery import RulespecGroupMonitoringAgentsWindowsAgent
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.valuespec import DropdownChoice
from cmk.utils.paths import local_agents_dir
from cmk.utils.rulesets.definition import RuleGroup


def validate_binaries(state: bool | None, varprefix: str) -> None:
    if state:
        path_to_dll = os.path.join(local_agents_dir, "windows", "OpenHardwareMonitorLib.dll")
        path_to_exe = os.path.join(local_agents_dir, "windows", "OpenHardwareMonitorCLI.exe")
        if not os.path.exists(path_to_dll) or not os.path.exists(path_to_exe):
            raise MKUserError(
                varprefix,
                _(
                    "Open Hardware Monitor files have been removed due to security reasons. "
                    "To use Open Hardware Monitor, you may download it from our site using commands as site user: "
                    "wget https://github.com/Checkmk/checkmk/blob/master/doc/treasures/windows/ohm/OpenHardwareMonitorCLI.exe -P local/share/check_mk/agents/windows/ "
                    "wget https://github.com/Checkmk/checkmk/blob/master/doc/treasures/windows/ohm/OpenHardwareMonitorLib.dll -P local/share/check_mk/agents/windows/"
                ),
            )


def _valuespec_agent_config_win_openhardwaremonitor() -> DropdownChoice[bool | None]:
    return DropdownChoice(
        title=_("OpenHardwareMonitor (Windows)"),
        help=_(
            "Adds a headless version of the OpenHardwareMonitor to the Windows agent. "
            "The agent will then automatically use this to provide readings of hardware "
            "sensors (temperature, fans, ...) to Checkmk. "
            "This does require .Net to be installed on the target system. Please leave this "
            "disabled if you have a different way to monitor sensors. You also don't need "
            "this if you are running the regular OpenHardwareMonitor software."
        ),
        validate=validate_binaries,
        choices=[
            (True, _("Deploy OpenHardwareMonitor (headless)")),
            (None, _("Do not deploy OpenHardwareMonitor (headless)")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupMonitoringAgentsWindowsAgent,
        name=RuleGroup.AgentConfig("win_openhardwaremonitor"),
        valuespec=_valuespec_agent_config_win_openhardwaremonitor,
    )
)
