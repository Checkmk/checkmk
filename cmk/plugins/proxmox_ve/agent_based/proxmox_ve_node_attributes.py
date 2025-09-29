#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable
from cmk.plugins.proxmox_ve.lib.node_attributes import SectionNodeAttributes


def parse_proxmox_ve_node_attributes(string_table: StringTable) -> SectionNodeAttributes:
    return SectionNodeAttributes.model_validate_json(json.loads(string_table[0][0]))


def host_label_function(section: SectionNodeAttributes) -> HostLabelGenerator:
    """
    Generate Proxmox VE node host labels.
    Labels:
        cmk/pve/entity:node:
            Fixed - shows that the object type is node.
        cmk/pve/cluster:<cluster_name>:
            The cluster of the Proxmox VE node.
    """
    yield HostLabel("cmk/pve/entity", "node")
    yield HostLabel("cmk/pve/cluster", section.cluster)


agent_section_proxmox_ve_node_attributes = AgentSection(
    name="proxmox_ve_node_attributes",
    parse_function=parse_proxmox_ve_node_attributes,
    host_label_function=host_label_function,
)
