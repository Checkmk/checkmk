#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.brocade.lib import DETECT_MLX
from cmk.plugins.lib.memory import check_element

_BROCADE_MLX_STATES: dict[int, tuple[State, str]] = {
    0: (State.WARN, "Slot is empty"),
    2: (State.WARN, "Module is going down"),
    3: (State.CRIT, "Rejected due to wrong configuration"),
    4: (State.CRIT, "Hardware is bad"),
    8: (State.WARN, "Configured / Stacking"),
    9: (State.WARN, "In power-up cycle"),
    10: (State.OK, "Running"),
    11: (State.OK, "Blocked for full height card"),
}


def _saveint(i: str) -> int:
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def _brocade_mlx_get_state(state: int) -> tuple[State, str]:
    return _BROCADE_MLX_STATES.get(state, (State.UNKNOWN, f"Unhandled state - {state}"))


def _brocade_mlx_combine_item(id_: str, descr: str) -> str:
    if descr == "":
        return id_
    descr = re.sub(" *Module", "", descr)
    return f"{id_} {descr}"


def parse_brocade_mlx(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_brocade_mlx = SNMPSection(
    name="brocade_mlx",
    detect=DETECT_MLX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.2.2.1.1",
            oids=["1", "2", "12", "24", "25"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1991.1.1.2.11.1.1",
            oids=[OIDEnd(), "5"],
        ),
    ],
    parse_function=parse_brocade_mlx,
)


# .
#   .--Overall Status------------------------------------------------------.
def discover_brocade_mlx_module(section: Sequence[StringTable]) -> DiscoveryResult:
    for module_id, module_descr, module_state, _mem_total, _mem_avail in section[0]:
        # do not inventorize modules reported as empty
        if module_state != "0":
            yield Service(item=_brocade_mlx_combine_item(module_id, module_descr))


def check_brocade_mlx_module(item: str, section: Sequence[StringTable]) -> CheckResult:
    for module_id, module_descr, module_state, _mem_total, _mem_avail in section[0]:
        if _brocade_mlx_combine_item(module_id, module_descr) == item:
            state, summary = _brocade_mlx_get_state(int(module_state))
            yield Result(state=state, summary=summary)
            return
    yield Result(state=State.UNKNOWN, summary="Module not found")


check_plugin_brocade_mlx_module_status = CheckPlugin(
    name="brocade_mlx_module_status",
    service_name="Status Module %s",
    sections=["brocade_mlx"],
    discovery_function=discover_brocade_mlx_module,
    check_function=check_brocade_mlx_module,
)


# .
#   .--Memory--------------------------------------------------------------.
_MemModule = dict[str, Any]


def _parse_brocade_mlx_module_mem(
    section: Sequence[StringTable],
) -> dict[str, _MemModule]:
    parsed: dict[str, _MemModule] = {}
    for module_id, module_descr, module_state, mem_total, mem_avail in section[0]:
        item = _brocade_mlx_combine_item(module_id, module_descr)
        try:
            _, state_readable = _brocade_mlx_get_state(int(module_state))
        except ValueError:
            state_readable = "Device did not return any state"

        parsed.setdefault(
            item,
            {
                "state_readable": state_readable,
                "descr": module_descr,
            },
        )

        try:
            parsed[item]["mem_total"] = int(mem_total)
        except ValueError:
            pass

        try:
            parsed[item]["mem_avail"] = int(mem_avail)
        except ValueError:
            pass

    return parsed


def discover_brocade_mlx_module_mem(section: Sequence[StringTable]) -> DiscoveryResult:
    for item, data in _parse_brocade_mlx_module_mem(section).items():
        # do not inventorize modules reported as empty or "Blocked for full height card"
        # and: monitor cpu only on NI-MLX and BR-MLX modules
        descr = data["descr"]
        if data["state_readable"] not in [
            "Slot is empty",
            "Blocked for full height card",
        ] and descr.startswith(("NI-MLX", "BR-MLX")):
            yield Service(item=item)


def check_brocade_mlx_module_mem(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    data = _parse_brocade_mlx_module_mem(section).get(item)
    if data is None:
        return

    state_readable = data["state_readable"]
    if state_readable.lower() != "running":
        yield Result(
            state=State.UNKNOWN,
            summary=f"Module is not running (Current State: {state_readable})",
        )
        return

    if "mem_total" not in data or "mem_avail" not in data:
        return

    levels = params.get("levels")
    if not isinstance(levels, tuple):
        memory_levels = None
    else:
        mode: Literal["abs_used", "perc_used"] = (
            "abs_used" if isinstance(levels[0], int) else "perc_used"
        )
        memory_levels = (mode, levels)
    yield from check_element(
        "Usage",
        data["mem_total"] - data["mem_avail"],
        data["mem_total"],
        memory_levels,
        metric_name="mem_used",
    )


check_plugin_brocade_mlx_module_mem = CheckPlugin(
    name="brocade_mlx_module_mem",
    service_name="Memory Module %s",
    sections=["brocade_mlx"],
    discovery_function=discover_brocade_mlx_module_mem,
    check_function=check_brocade_mlx_module_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={"levels": (80.0, 90.0)},
)


# .
#   .--CPU-----------------------------------------------------------------.
def discover_brocade_mlx_module_cpu(section: Sequence[StringTable]) -> DiscoveryResult:
    for module_id, module_descr, module_state, _mem_total, _mem_avail in section[0]:
        # do not inventorize modules reported as empty or "Blocked for full height card"
        # and: monitor cpu only on NI-MLX and BR-MLX modules
        if module_state not in {"0", "11"} and module_descr.startswith(("NI-MLX", "BR-MLX")):
            yield Service(item=_brocade_mlx_combine_item(module_id, module_descr))


def check_brocade_mlx_module_cpu(
    item: str, params: Mapping[str, Any], section: Sequence[StringTable]
) -> CheckResult:
    warn, crit = params["levels"]
    for module_id, module_descr, module_state, _mem_total, _mem_avail in section[0]:
        if _brocade_mlx_combine_item(module_id, module_descr) != item:
            continue

        if module_state != "10":
            yield Result(state=State.UNKNOWN, summary="Module is not in state running")
            return

        utils: dict[str, int | None] = {"1": None, "5": None, "60": None, "300": None}
        for oid_end, cpu_util in section[1]:
            for window in utils:
                if oid_end == f"{module_id}.1.{window}":
                    utils[window] = _saveint(cpu_util)

        if any(value is None for value in utils.values()):
            yield Result(
                state=State.UNKNOWN,
                summary="did not find all cpu utilization values in snmp output",
            )
            return

        cpu_util1, cpu_util5, cpu_util60, cpu_util300 = (
            utils["1"],
            utils["5"],
            utils["60"],
            utils["300"],
        )
        assert cpu_util1 is not None and cpu_util5 is not None
        assert cpu_util60 is not None and cpu_util300 is not None

        if cpu_util60 > crit:
            state = State.CRIT
            errorstring = "(!!)"
        elif cpu_util60 > warn:
            state = State.WARN
            errorstring = "(!)"
        else:
            state = State.OK
            errorstring = ""

        yield Result(
            state=state,
            summary=(
                f"CPU utilization was {cpu_util1}/{cpu_util5}/{cpu_util60}{errorstring}"
                f"/{cpu_util300}% for the last 1/5/60/300 sec"
            ),
        )
        yield Metric("cpu_util1", cpu_util1, boundaries=(0, 100))
        yield Metric("cpu_util5", cpu_util5, boundaries=(0, 100))
        yield Metric("cpu_util60", cpu_util60, levels=(warn, crit), boundaries=(0, 100))
        yield Metric("cpu_util300", cpu_util300, boundaries=(0, 100))
        return

    yield Result(state=State.UNKNOWN, summary="Module not found")


check_plugin_brocade_mlx_module_cpu = CheckPlugin(
    name="brocade_mlx_module_cpu",
    service_name="CPU utilization Module %s",
    sections=["brocade_mlx"],
    discovery_function=discover_brocade_mlx_module_cpu,
    check_function=check_brocade_mlx_module_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (80.0, 90.0)},
)
