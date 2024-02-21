#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v1 import HostLabel
from cmk.agent_based.v1.type_defs import HostLabelGenerator, StringTable
from cmk.agent_based.v2 import AgentSection
from cmk.plugins.lib.labels import custom_tags_to_valid_labels


def _parse_host_labels(string_table: StringTable) -> tuple[Mapping[str, str], Mapping[str, str]]:
    return json.loads(string_table[0][0]), json.loads(string_table[1][0])


def host_labels(section: tuple[Mapping[str, str], Mapping[str, str]]) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/azure/resource_group:
            This label contains the name of the resource group.

        cmk/azure/vm:instance:
            This label is set for all virtual machines monitored as hosts.

        cmk/azure/tag/{key}:{value}:
            These labels are yielded for each tag of a resource group or of a virtual machine which
            is monitored as a host. This can be configured via the rule 'Microsoft Azure'.
    """
    resource_info, tags = section
    yield HostLabel("cmk/azure/resource_group", resource_info["group_name"])

    if resource_info.get("vm_instance"):
        yield HostLabel("cmk/azure/vm", "instance")

    labels = custom_tags_to_valid_labels(tags)
    for key, value in labels.items():
        yield HostLabel(f"cmk/azure/tag/{key}", value)


# This section contains the tags of either a resource group or a VM montiored as a host
agent_section_azure_labels = AgentSection(
    name="azure_labels",
    parse_function=_parse_host_labels,
    host_label_function=host_labels,
)
