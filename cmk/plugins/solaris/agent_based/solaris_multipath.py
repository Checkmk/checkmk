#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Example output:
# <<<solaris_multipath>>>
# /dev/rdsk/c4t600601608CB02A00DCFD2EEB19A0E111d0s2 4 4

# Note: the number of total paths is not correct. After maintainance
# they is too high. Also in case of broken paths the number of total
# paths sometimes changes. So we just use that for informational
# output. The discovery remembers the number of operational paths
# and we check agains that later.


from collections.abc import Mapping
from typing import Any

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


def parse_solaris_multipath(string_table: StringTable) -> StringTable:
    return string_table


agent_section_solaris_multipath = AgentSection(
    name="solaris_multipath",
    parse_function=parse_solaris_multipath,
)


def discover_solaris_multipath(section: StringTable) -> DiscoveryResult:
    for device, _total, operational in section:
        item = device.split("/")[-1]
        yield Service(item=item, parameters={"levels": int(operational)})


def check_solaris_multipath(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for device, total, operational in section:
        if item == device.split("/")[-1]:
            operational_int = int(operational)
            total_int = int(total)

            # TODO: Clean this up! Compare to the multipath plugin.

            infotext = f"{operational_int} paths operational, {total_int} paths total"

            levels = params.get("levels")
            if levels is None:
                yield Result(
                    state=State.WARN,
                    summary=f"{infotext}, expected paths unknown, please redo service discovery",
                )
                return

            if isinstance(levels, tuple):
                warn, crit = levels
                warn_num = (warn / 100.0) * total_int
                crit_num = (crit / 100.0) * total_int
                levels_text = f" (Warning/ Critical at {warn_num:.0f}/ {crit_num:.0f})"
                info = f"paths active: {operational_int}"
                if operational_int <= crit_num:
                    yield Result(state=State.CRIT, summary=info + levels_text)
                elif operational_int <= warn_num:
                    yield Result(state=State.WARN, summary=info + levels_text)
                else:
                    yield Result(state=State.OK, summary=info)
                return

            expected = int(levels)  # should be int, just for legacy reasons
            if operational_int > expected:
                state = State.WARN
            elif expected == operational_int:
                state = State.OK
            elif expected >= operational_int * 2:  # less than half of paths operational
                state = State.CRIT
            else:
                state = State.WARN
            if state != State.OK:
                infotext += f", {expected} paths expected to be operational"

            yield Result(state=state, summary=infotext)
            return


check_plugin_solaris_multipath = CheckPlugin(
    name="solaris_multipath",
    service_name="Multipath %s",
    discovery_function=discover_solaris_multipath,
    check_function=check_solaris_multipath,
    check_ruleset_name="multipath",
    check_default_parameters={},  # overwritten by discovery
)
