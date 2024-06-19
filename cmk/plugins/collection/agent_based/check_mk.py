#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)
from cmk.plugins.lib.checkmk import CheckmkSection


def parse_checkmk_labels(string_table: StringTable) -> CheckmkSection:
    """
    Example:

        <<<check_mk>>>
        Version: 1.7.0
        BuildDate: Sep 15 2020
        AgentOS: windows
        Hostname: MSEDGEWIN10
        Architecture: 64bit
        OnlyFrom: 123.0.0.1
        OnlyFrom: 123.0.0.2

    The parsing mimics the behaviour of arguments passed to systemd units.
    On repetition either append (if another value is provided), or unset the value (if no value is
    provided).
    """

    section: dict[str, str | None] = {}

    for line in string_table:
        key = line[0][:-1].lower()
        val = " ".join(line[1:])
        section[key] = f"{section.get(key) or ''} {val}".strip() if len(line) > 1 else None

    return {"version": None, "agentos": None} | section


def host_label_function_labels(section: CheckmkSection) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/os_family:
            This label is set to the operating system as reported by the agent
            as "AgentOS" (such as "windows" or "linux").

        cmk/os_type:
            This label is set to the operating system as reported by the agent
            as "OSType" (such as "windows" or "linux").

        cmk/os_platform:
            This label is set to the platform as reported by the agent as "OSPlatform". In case
            "OSPlatform" is not set, the value of "AgentOS" is used.

        cmk/os_name:
            This label is set to the name of the operating system as reported by the agent as "OSName"

        cmk/os_version:
            This label is set to the version of the operating system as reported by the agent as "OSVersion"
    """

    if (agentos := section.get("agentos")) is not None:
        yield HostLabel("cmk/os_family", agentos)

    # `ostype` is a "floating" label and exists only if agent is new one(provides ostype data)
    if (ostype := section.get("ostype")) is not None:
        yield HostLabel("cmk/os_type", ostype)

    if (osplatform := section.get("osplatform", agentos)) is not None:
        yield HostLabel("cmk/os_platform", osplatform)

    if (osname := section.get("osname")) is not None:
        yield HostLabel("cmk/os_name", osname)

    if (osversion := section.get("osversion")) is not None:
        yield HostLabel("cmk/os_version", osversion)


agent_section_check_mk = AgentSection(
    name="check_mk",
    parse_function=parse_checkmk_labels,
    host_label_function=host_label_function_labels,
)


def inventory_checkmk(section: CheckmkSection) -> InventoryResult:
    yield Attributes(
        path=["networking"],
        inventory_attributes={"hostname": section.get("hostname")},
    )
    yield Attributes(
        path=["software", "applications", "checkmk-agent"],
        inventory_attributes={
            label: section[key]
            for key, label in (
                ("version", "version"),
                ("agentdirectory", "agent_directory"),
                ("datadirectory", "data_directory"),
                ("spooldirectory", "spool_directory"),
                ("pluginsdirectory", "plugins_directory"),
                ("localdirectory", "local_directory"),
                ("agentcontroller", "agent_controller_binary"),
            )
            if key in section
        },
    )


inventory_plugin_check_mk = InventoryPlugin(
    name="check_mk",
    inventory_function=inventory_checkmk,
)
