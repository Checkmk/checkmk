#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v1 import HostLabel
from cmk.agent_based.v1.type_defs import HostLabelGenerator, StringTable
from cmk.agent_based.v2 import AgentSection
from cmk.plugins.lib.labels import custom_tags_to_valid_labels


@dataclass(frozen=True, kw_only=True)
class LabelsSection:
    host_labels: Mapping[str, str | bool]
    tags: Mapping[str, str]


def _parse_host_labels(string_table: StringTable) -> LabelsSection:
    return LabelsSection(
        host_labels=json.loads(string_table[0][0]),
        tags=json.loads(string_table[1][0]),
    )


def host_labels(section: LabelsSection) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/azure/resource_group:
            This label contains the name of the resource group.

        cmk/azure/subscription_name:
            This label contains the name of the subscription.

        cmk/azure/subscription_id:
            This label contains the azure id of the subscription.

        cmk/azure/entity:subscription:
            This label is set for all hosts that are monitoring a subscription.

        cmk/azure/entity:resource_group:
            This label is set for all hosts that are monitoring a resource group.

        cmk/azure/entity:<entity_type>:
            This label is set for all hosts that are monitoring a resource.

        cmk/azure/vm:instance:
            This label is set for all virtual machines monitored as hosts.

        cmk/azure/tag/{key}:{value}:
            If the host is a resource group host
            this label is set for each tag of the resource group.
            If the host is a resource host,
            the label is set for each tag of the monitored resource,
            merged with the tags of its own resource group.
    """
    for label, value in section.host_labels.items():
        if label == "group_name":
            yield HostLabel("cmk/azure/resource_group", str(value))
            continue
        if label == "vm_instance":
            yield HostLabel("cmk/azure/vm", "instance")
            continue

        yield HostLabel(f"cmk/azure/{label}", str(value))

    if not section.tags:
        return

    tags = custom_tags_to_valid_labels(section.tags)
    for label, value in tags.items():
        yield HostLabel(f"cmk/azure/tag/{label}", value)


agent_section_azure_labels = AgentSection(
    name="azure_labels",
    parse_function=_parse_host_labels,
    host_label_function=host_labels,
)
