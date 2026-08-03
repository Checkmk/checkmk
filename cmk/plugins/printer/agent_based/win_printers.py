#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# Example output from agent:
# Put here the example output from your TCP-Based agent. If the
# <<<win_printers>>>
# PrinterStockholm                      0                   3                   0
# WH1_BC_O3_UPS                         0                   3                   0


import contextlib
from collections.abc import Mapping
from typing import Any, Final, NamedTuple

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
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


class PrinterQueue(NamedTuple):
    jobs: int
    status: int
    error: int


Section = Mapping[str, PrinterQueue]

_STATUS_MAP: Final = {
    1: "Other",
    2: "Unkown",
    3: "Idle",
    4: "Printing",
    5: "Warming Up",
    6: "Stopped Printing",
    7: "Offline",
}

_ERROR_MAP: Final = {
    0: "Unkown",
    1: "Other",
    2: "No Error",
    3: "Low Paper",
    4: "No Paper",
    5: "Low Toner",
    6: "No Toner",
    7: "Door Open",
    8: "Jammed",
    9: "Offline",
    10: "Service Requested",
    11: "Output Bin Full",
}


def parse_win_printers(string_table: StringTable) -> Section:
    parsed: dict[str, PrinterQueue] = {}
    for line in string_table:
        if len(line) < 4:
            continue
        with contextlib.suppress(ValueError):
            parsed.setdefault(
                " ".join(line[:-3]), PrinterQueue(int(line[-3]), int(line[-2]), int(line[-1]))
            )
    return parsed


def discover_win_printers(section: Section) -> DiscoveryResult:
    # Do not discover offline printers
    yield from (Service(item=item) for item, queue in section.items() if queue.error != 9)


def check_win_printers(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (queue := section.get(item)) is None:
        return

    yield from check_levels(
        queue.jobs,
        None,
        params.get("levels"),
        human_readable_func=str,
        infoname="Current jobs",
    )

    yield Result(state=State.OK, summary=f"State: {_STATUS_MAP[queue.status]}")

    if queue.error in params["crit_states"]:
        yield Result(state=State.CRIT, summary=f"Error state: {_ERROR_MAP[queue.error]}")
    elif queue.error in params["warn_states"]:
        yield Result(state=State.WARN, summary=f"Error state: {_ERROR_MAP[queue.error]}")


agent_section_win_printers = AgentSection(
    name="win_printers",
    parse_function=parse_win_printers,
)


check_plugin_win_printers = CheckPlugin(
    name="win_printers",
    service_name="Printer %s",
    discovery_function=discover_win_printers,
    check_function=check_win_printers,
    check_ruleset_name="windows_printer_queues",
    check_default_parameters={
        "warn_states": [8, 11],
        "crit_states": [9, 10],
    },
)
