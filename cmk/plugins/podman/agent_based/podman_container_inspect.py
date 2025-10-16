#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from cmk.agent_based.v2 import AgentSection, HostLabel, HostLabelGenerator, StringTable

from .lib import SectionPodmanContainerInspect


def parse_podman_container_inspect(
    string_table: StringTable,
) -> SectionPodmanContainerInspect | None:
    if not string_table[0]:
        return None

    return SectionPodmanContainerInspect.model_validate_json(string_table[0][0])


def host_label_function(section: SectionPodmanContainerInspect) -> HostLabelGenerator:
    """Generate podman container host labels.

    Labels:
        cmk/podman/object:container:
            Fixed - shows that the object type is container.
        cmk/podman/user:{user}:
            The user who owns the podman container.
        cmk/podman/pod:{pod}:
            The pod the container is running in (if applicable).
        cmk/podman/node:{node}:
            The node the container is running on.
    """
    yield HostLabel("cmk/podman/object", "container")
    yield HostLabel("cmk/podman/user", section.config.user)
    if section.pod:
        yield HostLabel("cmk/podman/pod", section.pod)
    yield HostLabel("cmk/podman/node", section.config.hostname)


agent_section_podman_container_inspect: AgentSection = AgentSection(
    name="podman_container_inspect",
    parse_function=parse_podman_container_inspect,
    host_label_function=host_label_function,
)
