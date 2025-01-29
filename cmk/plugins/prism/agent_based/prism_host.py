#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable
from cmk.plugins.lib.prism import load_json

Section = dict[str, Any]


def parse_prism_host(string_table: StringTable) -> Section:
    return load_json(string_table)


def host_label_prism_host(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/nutanix/object:
            This label is set to either "control_plane" for the host with the special agent, "node"
            for Nutanix nodes or "vm" for VMs hosted in Nutanix.

        cmk/os_name:
            This label is set to the name of the operating system as reported by the agent as "OSName"

        cmk/os_platform:
            This label is set to the platform as reported by the agent as "OSPlatform". In case
            "OSPlatform" is not set, the value of "AgentOS" is used.

    """
    yield HostLabel("cmk/nutanix/object", "node")
    yield HostLabel("cmk/os_platform", "nutanix")
    yield HostLabel("cmk/os_name", "Nutanix AHV")


agent_section_prism_host = AgentSection(
    name="prism_host",
    parse_function=parse_prism_host,
    host_label_function=host_label_prism_host,
)
