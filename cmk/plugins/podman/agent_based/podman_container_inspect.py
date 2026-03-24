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
            The host user who owns the Podman socket the container originates from.
        cmk/podman/pod:{pod}:
            The pod the container is running in (if applicable).
        cmk/docker_image:
            This label is set to the docker image if the corresponding host is
            a docker or podman container.
            For instance: "docker.io/library/nginx:latest"
        cmk/docker_image_name:
            This label is set to the docker image name if the corresponding host
            is a docker or podman container. For instance: "nginx".
        cmk/docker_image_version:
            This label is set to the docker images version if the corresponding
            host is a docker or podman container. For instance: "latest".
    """
    yield HostLabel("cmk/podman/object", "container")
    if section.socket_user:
        yield HostLabel("cmk/podman/user", section.socket_user)
    if section.pod:
        yield HostLabel("cmk/podman/pod", section.pod)

    if section.image_name:
        image = section.image_name
        yield HostLabel("cmk/docker_image", image)
        if "/" in image:
            __, image = image.rsplit("/", 1)
        if ":" in image:
            image_name, image_version = image.rsplit(":", 1)
            yield HostLabel("cmk/docker_image_name", image_name)
            yield HostLabel("cmk/docker_image_version", image_version)
        else:
            yield HostLabel("cmk/docker_image_name", image)


agent_section_podman_container_inspect: AgentSection = AgentSection(
    name="podman_container_inspect",
    parse_function=parse_podman_container_inspect,
    host_label_function=host_label_function,
)
