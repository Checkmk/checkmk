#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable

from .lib import SectionPodmanEngineStats


def parse_podman_engine(
    string_table: StringTable,
) -> SectionPodmanEngineStats | None:
    if not string_table[0]:
        return None

    return SectionPodmanEngineStats.model_validate_json(string_table[0][0])


def host_label_function(section: SectionPodmanEngineStats) -> HostLabelGenerator:
    """
    Generate podman engine host labels.
    Labels:
        cmk/podman/object:node:
            Fixed - shows that the object type is node.
        cmk/podman/host:
            The hostname of the podman engine.
    """
    yield HostLabel("cmk/podman/object", "node")
    yield HostLabel("cmk/podman/host", section.hostname)


agent_section_podman_engine = AgentSection(
    name="podman_engine",
    parse_function=parse_podman_engine,
    host_label_function=host_label_function,
)
