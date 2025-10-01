#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<mongodb_locks>>>
# activeClients readers 0
# activeClients total 53
# activeClients writers 0
# currentQueue readers 0
# currentQueue total 32
# currentQueue writers 5


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels  # we can only use v2 after migrating the ruleset!
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    StringTable,
)


def inventory_mongodb_locks(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_mongodb_locks(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for line in section:
        what, name, count = line
        param_name = "clients" if what.startswith("active") else "queue"
        metric_name = f"{param_name}_{name}_locks"

        yield from check_levels(
            int(count),
            metric_name=metric_name,
            levels_upper=params[metric_name] if metric_name in params else None,
            label=f"{param_name.title()}-{name.title()}",
        )


def parse_mongodb_locks(string_table: StringTable) -> StringTable:
    return string_table


agent_section_mongodb_locks = AgentSection(
    name="mongodb_locks",
    parse_function=parse_mongodb_locks,
)


check_plugin_mongodb_locks = CheckPlugin(
    name="mongodb_locks",
    service_name="MongoDB Locks",
    discovery_function=inventory_mongodb_locks,
    check_function=check_mongodb_locks,
    check_ruleset_name="mongodb_locks",
    check_default_parameters={},
)
