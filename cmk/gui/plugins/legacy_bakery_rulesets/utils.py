#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.agent_bakery import (
    RulespecGroupMonitoringAgentsAgentPlugins as RulespecGroupMonitoringAgentsAgentPlugins,
)
from cmk.gui.i18n import _


def windows_sections() -> list[tuple[str, str, bool, bool]]:
    # Tuple format:
    #     (section_name, display_name, enable_default, disable_default)
    # enable_default - indicates whether the section is checked by default in the
    #                  "Enabled sections (Windows agent)" ruleset
    # disable_default - indicates whether the section is checked by default in the
    #                   "Disabled sections (Windows agent)" ruleset
    return [
        ("check_mk", _("General information, agent version"), True, False),
        ("uptime", _("System uptime"), True, False),
        ("systemtime", _("System time (time synchronization)"), True, False),
        ("w32time_status", _("Windows Time service (status)"), True, False),
        ("w32time_peers", _("Windows Time service (peers)"), True, False),
        ("df", _("File systems (volumes, drives)"), True, False),
        ("mem", _("Memory and Pagefile"), True, False),
        ("ps", _("Currently running processes"), True, False),
        ("services", _("Installed, stopped and running services"), True, False),
        ("winperf", _("Various performance counters"), True, False),  # This is broken
        # There is no section winperf
        ("logwatch", _("Windows Event Logs"), True, False),
        ("logfiles", _("Messages in text log files"), True, False),
        ("fileinfo", _("Information about size, age and count of files"), True, False),
        ("plugins", _("Execute plug-ins in general"), True, False),
        ("local", _("Execute local scripts"), True, False),
        ("mrpe", _("Execute legacy monitoring plug-ins"), True, False),
        ("spool", _("Asynchronously spooled check results"), True, False),
        ("wmi_cpuload", _("CPU Load via WMI"), True, False),
        ("msexch", _("MS Exchange counters (various)"), True, False),
        ("wmi_webservices", _("Web Services"), True, False),
        ("dotnet_clrmemory", _(".Net/CLR Memory"), True, False),
        ("openhardwaremonitor", _("Hardware Sensors via OpenHardwareMonitor"), True, False),
        ("skype", _("Skype for Business"), True, False),
    ]
