#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package

from collections.abc import Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

InstancesSection = Mapping[str, int | None]
VersionSection = Mapping[str, str]


def parse_postgres_instances(string_table: StringTable) -> InstancesSection:
    parsed: dict[str, int | None] = {}
    is_single = False
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            is_single = True
            parsed.setdefault(instance_name, None)
        elif len(line) >= 4:
            if not is_single:
                instance_name = line[3].split("/")[-1].upper()
            try:
                parsed.setdefault(instance_name, None)
                parsed.update({instance_name: int(line[0])})
            except ValueError:
                pass

    return parsed


register.agent_section(
    name="postgres_instances",
    parse_function=parse_postgres_instances,
)


def parse_postgres_version(string_table: StringTable) -> VersionSection:
    parsed: dict[str, str] = {}
    instance_name = ""
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            instance_name = line[0][3:-3].upper()
            continue
        parsed.setdefault(instance_name, " ".join(line))
    return parsed


register.agent_section(
    name="postgres_version",
    parse_function=parse_postgres_version,
)


def discover_postgres_instances(
    section_postgres_instances: InstancesSection | None,
    section_postgres_version: VersionSection | None,
) -> DiscoveryResult:
    if section_postgres_instances is None:
        return

    yield from (Service(item=name) for name in section_postgres_instances)


def check_postgres_instances(
    item: str,
    section_postgres_instances: InstancesSection | None,
    section_postgres_version: VersionSection | None,
) -> CheckResult:
    pid = section_postgres_instances.get(item) if section_postgres_instances is not None else None
    version_info = (
        section_postgres_version.get(item) if section_postgres_version is not None else None
    )

    if pid is not None:
        yield Result(state=State.OK, summary=f"Status: running with PID {pid}")
    else:
        yield Result(
            state=State.CRIT,
            summary=(
                f"Status: instance {item} is not running or postgres DATADIR name is not identical "
                f"with instance name"
            ),
        )
    if version_info is not None:
        yield Result(state=State.OK, summary=f"Version: {version_info}")
    else:
        yield Result(state=State.OK, summary="Version: not found")


register.check_plugin(
    name="postgres_instances",
    sections=["postgres_instances", "postgres_version"],
    service_name="PostgreSQL Instance %s",
    discovery_function=discover_postgres_instances,
    check_function=check_postgres_instances,
)
