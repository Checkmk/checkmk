#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.proxmox_ve.lib.node_allocation import SectionNodeAllocation


def parse_proxmox_ve_node_allocation(string_table: StringTable) -> SectionNodeAllocation:
    return SectionNodeAllocation.model_validate_json(json.loads(string_table[0][0]))


agent_section_proxmox_ve_node_allocation = AgentSection(
    name="proxmox_ve_node_allocation",
    parse_function=parse_proxmox_ve_node_allocation,
)
