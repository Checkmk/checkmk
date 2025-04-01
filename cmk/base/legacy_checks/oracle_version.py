#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.base.check_legacy_includes.oracle import (
    oracle_handle_ora_errors,
    oracle_handle_ora_errors_discovery,
)

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

# <<<oracle_version>>>
# XE Oracle Database 11g Express Edition Release 11.2.0.2.0 - 64bit Production


def inventory_oracle_version(section: StringTable) -> DiscoveryResult:
    oracle_handle_ora_errors_discovery(section)
    yield from [Service(item=line[0]) for line in section if len(line) >= 2]


def check_oracle_version(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            err = oracle_handle_ora_errors(line)
            if err is False:
                continue
            elif isinstance(err, Result):
                yield err
            elif err is None:
                pass
            else:
                assert_never(err)

            yield Result(state=State.OK, summary="Version: " + " ".join(line[1:]))
            return
    yield Result(state=State.UNKNOWN, summary="no version information, database might be stopped")


def parse_oracle_version(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_version = AgentSection(
    name="oracle_version",
    parse_function=parse_oracle_version,
)

check_plugin_oracle_version = CheckPlugin(
    name="oracle_version",
    service_name="ORA Version %s",
    discovery_function=inventory_oracle_version,
    check_function=check_oracle_version,
)
