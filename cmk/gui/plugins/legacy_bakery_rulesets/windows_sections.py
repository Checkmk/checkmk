#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Catalogue of Windows agent sections, shared by the rule sets for enabling and disabling
sections."""

from collections.abc import Mapping, Sequence
from typing import NamedTuple

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import MultipleChoiceElement


class WindowsSection(NamedTuple):
    name: str
    title: Title
    enabled_by_default: bool
    """Preselected in the "Enabled sections (Windows agent)" rule set"""
    disabled_by_default: bool
    """Preselected in the "Disabled sections (Windows agent)" rule set"""


WINDOWS_SECTIONS: Sequence[WindowsSection] = (
    WindowsSection("check_mk", Title("General information, agent version"), True, False),
    WindowsSection("uptime", Title("System uptime"), True, False),
    WindowsSection("systemtime", Title("System time (time synchronization)"), True, False),
    WindowsSection("w32time_status", Title("Windows Time service (status)"), True, False),
    WindowsSection("w32time_peers", Title("Windows Time service (peers)"), True, False),
    WindowsSection("df", Title("File systems (volumes, drives)"), True, False),
    WindowsSection("mem", Title("Memory and Pagefile"), True, False),
    WindowsSection("ps", Title("Currently running processes"), True, False),
    WindowsSection("services", Title("Installed, stopped and running services"), True, False),
    # This is broken: there is no section winperf
    WindowsSection("winperf", Title("Various performance counters"), True, False),
    WindowsSection("logwatch", Title("Windows Event Logs"), True, False),
    WindowsSection("logfiles", Title("Messages in text log files"), True, False),
    WindowsSection(
        "fileinfo", Title("Information about size, age and count of files"), True, False
    ),
    WindowsSection("plugins", Title("Execute plug-ins in general"), True, False),
    WindowsSection("local", Title("Execute local scripts"), True, False),
    WindowsSection("mrpe", Title("Execute legacy monitoring plug-ins"), True, False),
    WindowsSection("spool", Title("Asynchronously spooled check results"), True, False),
    WindowsSection("wmi_cpuload", Title("CPU load via WMI"), True, False),
    WindowsSection("msexch", Title("MS Exchange counters (various)"), True, False),
    WindowsSection("wmi_webservices", Title("Web Services"), True, False),
    WindowsSection("dotnet_clrmemory", Title(".Net/CLR Memory"), True, False),
    WindowsSection(
        "openhardwaremonitor", Title("Hardware Sensors via OpenHardwareMonitor"), True, False
    ),
    WindowsSection("skype", Title("Skype for Business"), True, False),
)


def section_choices() -> Sequence[MultipleChoiceElement]:
    return [MultipleChoiceElement(name=s.name, title=s.title) for s in WINDOWS_SECTIONS]


def migrate_sections(value: object) -> Mapping[str, object]:
    """The old rule sets stored the selected section names as a bare list."""
    if isinstance(value, dict) and "sections" in value:
        return value
    if isinstance(value, list):
        return {"sections": value}
    raise ValueError(f"Unexpected value: {value!r}")
