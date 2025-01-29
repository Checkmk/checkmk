#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.prism import load_json

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_info(string_table: StringTable) -> Section:
    return load_json(string_table)


def host_label_prism_info(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/nutanix/object:
            This label is set to either "control_plane" for the host with the special agent, "node"
            for Nutanix nodes or "vm" for VMs hosted in Nutanix.

    """
    yield HostLabel("cmk/nutanix/object", "control_plane")


agent_section_prism_info = AgentSection(
    name="prism_info",
    parse_function=parse_prism_info,
    host_label_function=host_label_prism_info,
)


def discovery_prism_info(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_prism_info(section: Section) -> CheckResult:
    if section:
        summary = (
            f"Name: {section.get('name')}, "
            f"Version: {section.get('version')}, "
            f"Nodes: {section.get('num_nodes')}"
        )

        yield Result(
            state=State.OK,
            summary=summary,
        )


check_plugin_prism_info = CheckPlugin(
    name="prism_info",
    service_name="NTNX Cluster",
    sections=["prism_info"],
    discovery_function=discovery_prism_info,
    check_function=check_prism_info,
)
