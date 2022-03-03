#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import Attributes, HostLabel, register
from .agent_based_api.v1.type_defs import HostLabelGenerator, InventoryResult, StringTable
from .utils.checkmk import CheckmkSection


# TODO: This is duplicate code with cmk/core_helpers/agent.py
# For various layering reasons, it's not as easy to deduplicate
# as you'd think. I am thinking about this. - mo, 2021-12
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

    section: dict[str, Optional[str]] = {}

    for line in string_table:
        key = line[0][:-1].lower()
        val = " ".join(line[1:])
        section[key] = f"{section.get(key) or ''} {val}".strip() if len(line) > 1 else None

    return {"version": None, "agentos": None, **section}


def host_label_function_labels(section: CheckmkSection) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/os_family:
            This label is set to the operating system as reported by the agent
            as "AgentOS" (such as "windows" or "linux").

    """
    if (agentos := section.get("agentos")) is not None:
        yield HostLabel("cmk/os_family", agentos)


register.agent_section(
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


register.inventory_plugin(
    name="check_mk",
    inventory_function=inventory_checkmk,
)
