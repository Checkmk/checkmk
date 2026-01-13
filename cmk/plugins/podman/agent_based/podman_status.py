#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections.abc import Sequence

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

type Section = Sequence[Error]


class Error(BaseModel, frozen=True):
    endpoint: str
    message: str


def parse_podman_status(string_table: StringTable) -> Section:
    return [
        Error.model_validate(content)
        for line in string_table
        if line and (content := json.loads(line[0]))
    ]


agent_section_podman_status: AgentSection = AgentSection(
    name="podman_errors",
    parsed_section_name="podman_status",
    parse_function=parse_podman_status,
)


def discover_podman_status(section: Section) -> DiscoveryResult:
    yield Service()


def check_podman_status(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No errors")
        return

    yield Result(
        state=State.CRIT,
        summary=f"Errors: {len(section)}, see details",
        details="\n".join(f"{error.endpoint}: {error.message}" for error in section),
    )


check_plugin_podman_status = CheckPlugin(
    name="podman_status",
    service_name="Podman status",
    discovery_function=discover_podman_status,
    check_function=check_podman_status,
)
