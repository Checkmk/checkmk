#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from collections.abc import Iterable
from contextlib import suppress

from cmk.ccc.cpu_tracking import Snapshot

from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.fetcher import FetcherType, SourceInfo

__all__ = ["make_timing_results"]


def make_timing_results(
    total_times: Snapshot,
    fetched: Iterable[tuple[SourceInfo, Snapshot]],
    *,
    perfdata_with_times: bool,
) -> ActiveCheckResult:
    summary: defaultdict[str, Snapshot] = defaultdict(Snapshot.null)
    for source, duration in fetched:
        total_times += duration
        with suppress(KeyError):
            summary[
                {
                    FetcherType.PIGGYBACK: "agent",
                    FetcherType.PROGRAM: "ds",
                    FetcherType.SPECIAL_AGENT: "ds",
                    FetcherType.SNMP: "snmp",
                    FetcherType.TCP: "agent",
                }[source.fetcher_type]
            ] += duration

    infotext = "execution time %.1f sec" % total_times.process.elapsed
    if not perfdata_with_times:
        return ActiveCheckResult(
            state=0,
            summary=infotext,
            details=(),
            metrics=("execution_time=%.3f" % total_times.process.elapsed,),
        )

    perfdata = [
        "execution_time=%.3f" % total_times.process.elapsed,
        "user_time=%.3f" % total_times.process.user,
        "system_time=%.3f" % total_times.process.system,
        "children_user_time=%.3f" % total_times.process.children_user,
        "children_system_time=%.3f" % total_times.process.children_system,
    ]

    for phase, duration in summary.items():
        perfdata.append(f"cmk_time_{phase}={duration.idle:.3f}")

    return ActiveCheckResult(state=0, summary=infotext, details=(), metrics=perfdata)
