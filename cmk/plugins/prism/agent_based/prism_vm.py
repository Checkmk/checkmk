#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable
from cmk.plugins.lib.prism import load_json

Section = Mapping[str, Any]


def parse_prism_vm(string_table: StringTable) -> Section:
    return load_json(string_table)


def host_label_prism_vm(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/nutanix/object:
            This label is set to either "control_plane" for the host with the special agent, "node"
            for Nutanix nodes or "vm" for VMs hosted in Nutanix.

    """
    yield HostLabel("cmk/nutanix/object", "vm")


agent_section_prism_vm = AgentSection(
    name="prism_vm",
    parse_function=parse_prism_vm,
    host_label_function=host_label_prism_vm,
)
