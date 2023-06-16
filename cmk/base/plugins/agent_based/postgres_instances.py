#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package

from collections.abc import Mapping
from typing import Optional

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

_InstancesSection = Mapping[str, Optional[int]]


def parse_postgres_instances(string_table: StringTable) -> _InstancesSection:
    parsed: dict[str, Optional[int]] = {}
    is_single = False
    for line in string_table:
        if line[0].startswith("[[[") and line[0].endswith("]]]"):
            db_id = line[0][3:-3]
            is_single = True
            parsed.setdefault(db_id.upper(), None)
        elif len(line) >= 4:
            if not is_single:
                db_id = line[3].split("/")[-1]
            try:
                parsed.setdefault(db_id.upper(), None)
                parsed.update({db_id.upper(): int(line[0])})
            except ValueError:
                pass

    return parsed


register.agent_section(
    name="postgres_instances",
    parse_function=parse_postgres_instances,
)


def discover_postgres_instances(section: _InstancesSection) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_postgres_instances(item: str, section: _InstancesSection) -> CheckResult:
    if (pid := section.get(item)) is not None:
        yield Result(state=State.OK, summary=f"Status: running with PID {pid}")
    else:
        yield Result(
            state=State.CRIT,
            summary=(
                f"Instance {item} not running or postgres DATADIR name is not identical with "
                "instance name."
            ),
        )


register.check_plugin(
    name="postgres_instances",
    service_name="PostgreSQL Instance %s",
    discovery_function=discover_postgres_instances,
    check_function=check_postgres_instances,
)
