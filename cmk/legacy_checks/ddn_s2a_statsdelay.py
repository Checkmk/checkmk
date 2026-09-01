#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ddn_s2a.lib import parse_ddn_s2a_api_response


@dataclass(frozen=True, kw_only=True)
class Section:
    """Histograms binning read/write events by their delay.

    All sequences share the binning given by :attr:`time_intervals`.
    """

    time_intervals: Sequence[float]
    host_reads: Sequence[int]
    host_writes: Sequence[int]
    disk_reads: Sequence[int]
    disk_writes: Sequence[int]


def parse_ddn_s2a_statsdelay(string_table: StringTable) -> Section:
    parsed = parse_ddn_s2a_api_response(string_table)
    return Section(
        # Regarding the special treatment of the >10.0 value here: This API does not provide
        # more detailed information than this. We assume a value of 30, but we really have no way
        # of knowing. These events are usually very rare (~two in a million).
        time_intervals=[
            30.0 if x == ">10.0" else float(x) for x in parsed["time_interval_in_seconds"]
        ],
        host_reads=[int(e) for e in parsed["host_reads"]],
        host_writes=[int(e) for e in parsed["host_writes"]],
        disk_reads=[int(e) for e in parsed["disk_reads"]],
        disk_writes=[int(e) for e in parsed["disk_writes"]],
    )


def discover_ddn_s2a_statsdelay(section: Section) -> DiscoveryResult:
    yield Service(item="Disk")
    yield Service(item="Host")


def check_ddn_s2a_statsdelay(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    # The API gives information about the delay statistics in a histogram,
    # binning read/write events by their delay. The individual bins are
    # counters. To get a picture of the current delay stats, we subtract
    # the previous check period's histogram from the current one. This means
    # that the averaging in particular is always across one check period,
    # and the respective min and max values refer to events within the last
    # check period.
    match item:
        case "Disk":
            reads, writes = section.disk_reads, section.disk_writes
        case "Host":
            reads, writes = section.host_reads, section.host_writes
        case _:
            return

    value_store = get_value_store()
    old_intervals = value_store.get("time_intervals")
    old_reads = value_store.get("reads")
    old_writes = value_store.get("writes")

    value_store["time_intervals"] = section.time_intervals
    value_store["reads"] = reads
    value_store["writes"] = writes

    if old_intervals is None or old_reads is None or old_writes is None:
        raise IgnoreResultsError("Initializing")
    if old_intervals != section.time_intervals:
        raise IgnoreResultsError(
            "Histograms not comparable - Time intervals have changed. Reinitializing."
        )

    reads_since_last_check = [new - old for new, old in zip(reads, old_reads)]
    writes_since_last_check = [new - old for new, old in zip(writes, old_writes)]
    if not any(reads_since_last_check) and not any(writes_since_last_check):
        raise IgnoreResultsError("No writes or reads since last check")

    read_min, read_max, read_avg = _histogram_stats(section.time_intervals, reads_since_last_check)
    yield from _check_wait(
        "Average read wait", read_avg, params.get("read_avg"), "disk_average_read_wait"
    )
    yield from _check_wait("Min. read wait", read_min, params.get("read_min"), "disk_min_read_wait")
    yield from _check_wait("Max. read wait", read_max, params.get("read_max"), "disk_max_read_wait")

    write_min, write_max, write_avg = _histogram_stats(
        section.time_intervals, writes_since_last_check
    )
    yield from _check_wait(
        "Average write wait", write_avg, params.get("write_avg"), "disk_average_write_wait"
    )
    yield from _check_wait(
        "Min. write wait", write_min, params.get("write_min"), "disk_min_write_wait"
    )
    yield from _check_wait(
        "Max. write wait", write_max, params.get("write_max"), "disk_max_write_wait"
    )


def _histogram_stats(
    time_intervals: Sequence[float], values: Sequence[int]
) -> tuple[float, float, float]:
    """Return the minimum, maximum and average delay of the events in the histogram."""
    if not (event_count := sum(values)):
        return 0.0, 0.0, 0.0

    populated = [interval for interval, value in zip(time_intervals, values) if value]
    total_time = sum(interval * value for interval, value in zip(time_intervals, values))
    return populated[0], populated[-1], total_time / event_count


def _check_wait(
    label: str, value: float, levels: tuple[float, float] | None, metric_name: str
) -> CheckResult:
    summary = f"{label}: {value:.2f} s"
    state = State.OK
    if levels:
        warn, crit = levels
        if value >= crit:
            state = State.CRIT
        elif value >= warn:
            state = State.WARN
        if state is not State.OK:
            summary += f" (warn/crit at {warn:.2f}/{crit:.2f} s)"

    yield Result(state=state, summary=summary)
    yield Metric(metric_name, value, levels=levels or None)


agent_section_ddn_s2a_statsdelay = AgentSection(
    name="ddn_s2a_statsdelay",
    parse_function=parse_ddn_s2a_statsdelay,
)


check_plugin_ddn_s2a_statsdelay = CheckPlugin(
    name="ddn_s2a_statsdelay",
    service_name="DDN S2A Delay %s",
    discovery_function=discover_ddn_s2a_statsdelay,
    check_function=check_ddn_s2a_statsdelay,
    check_ruleset_name="ddn_s2a_wait",
    check_default_parameters={
        "read_avg": (0.1, 0.2),
        "write_avg": (0.1, 0.2),
    },
)
