#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

from collections.abc import Mapping, Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_value_store, IgnoreResultsError, StringTable
from cmk.base.check_legacy_includes.ddn_s2a import parse_ddn_s2a_api_response

check_info = {}

type SectionStatsDelay = Mapping[str, Sequence[str] | Sequence[int] | Sequence[float]]


def parse_ddn_s2a_statsdelay(string_table: StringTable) -> SectionStatsDelay:
    parsed: dict[str, Sequence[str] | Sequence[int] | Sequence[float]] = {
        **parse_ddn_s2a_api_response(string_table)
    }

    for key in ["host_reads", "host_writes", "disk_reads", "disk_writes"]:
        parsed[key] = [int(e) for e in parsed[key]]

    # Regarding the special treatment of the >10.0 value here: This API does not provide
    # more detailed information than this. We assume a value of 30, but we really have no way
    # of knowing. These events are usually very rare (~two in a million).
    parsed["time_interval_in_seconds"] = [
        float(x) if x != ">10.0" else 30 for x in parsed["time_interval_in_seconds"]
    ]
    return parsed


def discover_ddn_s2a_statsdelay(parsed):
    yield "Disk", {}
    yield "Host", {}


def check_ddn_s2a_statsdelay(item, params, parsed):
    # The API gives information about the delay statistics in a histogram,
    # binning read/write events by their delay. The individual bins are
    # counters. To get a picture of the current delay stats, we subtract
    # the previous check period's histogram from the current one. This means
    # that the averaging in particular is always across one check period,
    # and the respective min and max values refer to events within the last
    # check period.

    def subtract_histograms(histogram1, histogram2):
        return [v1 - v2 for v1, v2 in zip(histogram1, histogram2)]

    def is_zero(histogram: Sequence[int]) -> bool:
        return not any(histogram)

    def histogram_min(time_intervals, values):
        for interval, value in zip(time_intervals, values):
            if value != 0:
                return interval
        return None

    def histogram_max(time_intervals, values):
        for interval, value in list(zip(time_intervals, values))[::-1]:
            if value != 0:
                return interval
        return None

    def histogram_avg(time_intervals, values):
        number_of_values = 0
        total_time = 0.0
        for time_interval, value in zip(time_intervals, values):
            number_of_values += value
            total_time += time_interval * value
        return total_time / number_of_values  # fixed: true-division

    def _check_levels(infotext_formatstring, value, levels, perfname):
        infotext = infotext_formatstring % value
        if not levels:
            return 0, infotext, [(perfname, value)]
        warn, crit = levels
        levelstext = f" (warn/crit at {warn:.2f}/{crit:.2f} s)"
        perfdata = [(perfname, value, warn, crit)]
        if value >= crit:
            status = 2
            infotext += levelstext
        elif value >= warn:
            status = 1
            infotext += levelstext
        else:
            status = 0
        return status, infotext, perfdata

    value_store = get_value_store()

    time_intervals = parsed["time_interval_in_seconds"]
    if item == "Disk":
        reads = parsed["disk_reads"]
        writes = parsed["disk_writes"]
    elif item == "Host":
        reads = parsed["host_reads"]
        writes = parsed["host_writes"]

    old_intervals = value_store.get("time_intervals")
    old_reads = value_store.get("reads")
    old_writes = value_store.get("writes")

    value_store["time_intervals"] = time_intervals
    value_store["reads"] = reads
    value_store["writes"] = writes

    if old_intervals is None:
        raise IgnoreResultsError("Initializing")
    if old_intervals != time_intervals:
        raise IgnoreResultsError(
            "Histograms not comparable - Time intervals have changed. Reinitializing."
        )

    reads_since_last_check = subtract_histograms(reads, old_reads)
    writes_since_last_check = subtract_histograms(writes, old_writes)
    if is_zero(reads_since_last_check) and is_zero(writes_since_last_check):
        raise IgnoreResultsError("No writes or reads since last check")

    if not is_zero(reads_since_last_check):
        read_min = histogram_min(time_intervals, reads_since_last_check)
        read_max = histogram_max(time_intervals, reads_since_last_check)
        read_avg = histogram_avg(time_intervals, reads_since_last_check)
    else:
        read_min, read_max, read_avg = 0, 0, 0

    yield _check_levels(
        "Average read wait: %.2f s", read_avg, params.get("read_avg"), "disk_average_read_wait"
    )
    yield _check_levels(
        "Min. read wait: %.2f s", read_min, params.get("read_min"), "disk_min_read_wait"
    )
    yield _check_levels(
        "Max. read wait: %.2f s", read_max, params.get("read_max"), "disk_max_read_wait"
    )

    if not is_zero(writes_since_last_check):
        write_min = histogram_min(time_intervals, writes_since_last_check)
        write_max = histogram_max(time_intervals, writes_since_last_check)
        write_avg = histogram_avg(time_intervals, writes_since_last_check)
    else:
        write_min, write_max, write_avg = 0, 0, 0

    yield _check_levels(
        "Average write wait: %.2f s", write_avg, params.get("write_avg"), "disk_average_write_wait"
    )
    yield _check_levels(
        "Min. write wait: %.2f s", write_min, params.get("write_min"), "disk_min_write_wait"
    )
    yield _check_levels(
        "Max. write wait: %.2f s", write_max, params.get("write_max"), "disk_max_write_wait"
    )


check_info["ddn_s2a_statsdelay"] = LegacyCheckDefinition(
    name="ddn_s2a_statsdelay",
    parse_function=parse_ddn_s2a_statsdelay,
    service_name="DDN S2A Delay %s",
    discovery_function=discover_ddn_s2a_statsdelay,
    check_function=check_ddn_s2a_statsdelay,
    check_ruleset_name="ddn_s2a_wait",
    check_default_parameters={
        "read_avg": (0.1, 0.2),
        "write_avg": (0.1, 0.2),
    },
)
