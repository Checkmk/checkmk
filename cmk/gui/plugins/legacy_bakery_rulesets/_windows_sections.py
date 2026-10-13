#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Catalogue of Windows agent sections, shared by the rule sets for enabling and disabling
sections."""

from collections.abc import Sequence
from typing import NamedTuple

from cmk.gui.i18n import _


class WindowsSection(NamedTuple):
    name: str
    title: str
    enabled_by_default: bool
    """Preselected in the "Enabled sections (Windows agent)" rule set"""
    disabled_by_default: bool
    """Preselected in the "Disabled sections (Windows agent)" rule set"""


def windows_sections() -> Sequence[WindowsSection]:
    return (
        WindowsSection("check_mk", _("General information, agent version"), True, False),
        WindowsSection("uptime", _("System uptime"), True, False),
        WindowsSection("systemtime", _("System time (time synchronization)"), True, False),
        WindowsSection("w32time_status", _("Windows Time service (status)"), True, False),
        WindowsSection("w32time_peers", _("Windows Time service (peers)"), True, False),
        WindowsSection("df", _("File systems (volumes, drives)"), True, False),
        WindowsSection("mem", _("Memory and Pagefile"), True, False),
        WindowsSection("ps", _("Currently running processes"), True, False),
        WindowsSection("services", _("Installed, stopped and running services"), True, False),
        # This is broken: there is no section winperf
        WindowsSection("winperf", _("Various performance counters"), True, False),
        WindowsSection("logwatch", _("Windows Event Logs"), True, False),
        WindowsSection("logfiles", _("Messages in text log files"), True, False),
        WindowsSection(
            "fileinfo", _("Information about size, age and count of files"), True, False
        ),
        WindowsSection("plugins", _("Execute plug-ins in general"), True, False),
        WindowsSection("local", _("Execute local scripts"), True, False),
        WindowsSection("mrpe", _("Execute legacy monitoring plug-ins"), True, False),
        WindowsSection("spool", _("Asynchronously spooled check results"), True, False),
        WindowsSection("wmi_cpuload", _("CPU load via WMI"), True, False),
        WindowsSection("msexch", _("MS Exchange counters (various)"), True, False),
        WindowsSection("wmi_webservices", _("Web Services"), True, False),
        WindowsSection("dotnet_clrmemory", _(".Net/CLR Memory"), True, False),
        WindowsSection(
            "openhardwaremonitor", _("Hardware Sensors via OpenHardwareMonitor"), True, False
        ),
        WindowsSection("skype", _("Skype for Business"), True, False),
    )
