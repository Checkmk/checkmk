#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from cmk.agent_based.v2 import AgentSection, StringTable

from .lib import SectionPodmanContainerStats


def parse_podman_container_stats(
    string_table: StringTable,
) -> SectionPodmanContainerStats | None:
    if not string_table[0]:
        return None

    return SectionPodmanContainerStats.model_validate_json(string_table[0][0])


agent_section_podman_container_stats: AgentSection = AgentSection(
    name="podman_container_stats",
    parse_function=parse_podman_container_stats,
)
