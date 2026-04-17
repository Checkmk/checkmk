#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict

import dateutil.parser

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.legacy_includes.ibm_mq import is_ibm_mq_service_vanished

# <<<ibm_mq_queues:sep(10)>>>
# QMNAME(MY.TEST)                                           STATUS(RUNNING)
# 5724-H72 (C) Copyright IBM Corp. 1994, 2015.
# Starting MQSC for queue manager MY.TEST.
#
#
# AMQ8409: Display Queue details.
#    QUEUE(SAMPLE.IN)
#    TYPE(QLOCAL)                            MAXDEPTH(7800)
# AMQ8409: Display Queue details.
#    QUEUE(SAMPLE.OUT)                       TYPE(QLOCAL)
#    MAXDEPTH(5000)
# AMQ8450: Display queue status details.
#    QUEUE(SAMPLE.IN)                        TYPE(QUEUE)
#    CURDEPTH(5)                             LGETDATE(2017-03-09)
#    LGETTIME(15.14.45)                      LPUTDATE(2017-03-14)
#    LPUTTIME(08.37.50)                      MONQ(MEDIUM)
#    MSGAGE(502413)                          QTIME(999999999, 999999999)
# AMQ8450: Display queue status details.
#    QUEUE(SAMPLE.OUT)
#    TYPE(QUEUE)                             CURDEPTH(1)
#    LGETDATE( )                             LGETTIME( )
#    LPUTDATE( )                             LPUTTIME( )
#    MONQ(MEDIUM)                            MSGAGE(0)
#    QTIME(10404, 8223)
# 2 MQSC commands read.
# No commands have a syntax error.
# All valid MQSC commands were processed.


Section = Mapping[str, Mapping[str, str]]


class _ProcLevels(TypedDict, total=False):
    upper: tuple[int, int]
    lower: tuple[int, int]


class _QueueParams(TypedDict, total=False):
    curdepth: tuple[int | None, int | None]
    curdepth_perc: tuple[float | None, float | None]
    msgage: tuple[int, int]
    lgetage: tuple[int, int]
    lputage: tuple[int, int]
    ipprocs: _ProcLevels
    opprocs: _ProcLevels


def discover_ibm_mq_queues(section: Section) -> DiscoveryResult:
    for service_name in section:
        if ":" not in service_name:
            # Do not show queue manager entry in inventory
            continue
        yield Service(item=service_name)


QTIME_PATTERN = re.compile(r"^([0-9]*),[\s]*([0-9]*)$")


def check_ibm_mq_queues(item: str, params: _QueueParams, section: Section) -> CheckResult:
    if is_ibm_mq_service_vanished(item, section):
        return
    data = section[item]

    if "CURDEPTH" in data:
        cur_depth = data.get("CURDEPTH")
        max_depth = data.get("MAXDEPTH")
        yield from ibm_mq_depth(cur_depth, max_depth, params)

    if "MSGAGE" in data:
        msg_age = data.get("MSGAGE")
        yield from ibm_mq_msg_age(msg_age, params)

    if "LGETDATE" in data:
        mq_date = data.get("LGETDATE")
        mq_time = data.get("LGETTIME")
        agent_timestamp = ibm_mq_agent_timestamp(item, section)
        yield from ibm_mq_last_age(
            mq_date, mq_time, agent_timestamp, "Last get", params.get("lgetage")
        )

    if "LPUTDATE" in data:
        mq_date = data.get("LPUTDATE")
        mq_time = data.get("LPUTTIME")
        agent_timestamp = ibm_mq_agent_timestamp(item, section)
        yield from ibm_mq_last_age(
            mq_date, mq_time, agent_timestamp, "Last put", params.get("lputage")
        )

    if "IPPROCS" in data:
        cnt = data["IPPROCS"]
        yield from ibm_mq_procs(cnt, "Open input handles", params.get("ipprocs"), "ipprocs")

    if "OPPROCS" in data:
        cnt = data["OPPROCS"]
        yield from ibm_mq_procs(cnt, "Open output handles", params.get("opprocs"), "opprocs")

    if "QTIME" in data:
        qtimes = data["QTIME"]
        if qtimes_match := QTIME_PATTERN.match(qtimes):
            qtime_short = qtimes_match.group(1)
            qtime_long = qtimes_match.group(2)
            yield from ibm_mq_get_qtime(qtime_short, "Qtime short", "qtime_short")
            yield from ibm_mq_get_qtime(qtime_long, "Qtime long", "qtime_long")


def ibm_mq_depth(cur_depth: str | None, max_depth: str | None, params: _QueueParams) -> CheckResult:
    cur_depth_int = int(cur_depth) if cur_depth else None
    max_depth_int = int(max_depth) if max_depth else None

    val = cur_depth_int if cur_depth_int is not None else 0
    boundaries = (0, max_depth_int) if max_depth_int is not None else None

    raw_abs = params.get("curdepth")
    abs_warn, abs_crit = raw_abs if raw_abs else (None, None)
    abs_level_pair: tuple[int, int] | None = (
        (abs_warn, abs_crit) if abs_warn is not None and abs_crit is not None else None
    )

    yield from check_levels(
        val,
        label="Queue depth",
        levels_upper=("fixed", abs_level_pair)
        if abs_level_pair is not None
        else ("no_levels", None),
        metric_name="curdepth",
        render_func=str,
        boundaries=boundaries,
    )

    if cur_depth_int and max_depth_int:
        raw_perc = params.get("curdepth_perc")
        if raw_perc:
            perc_warn, perc_crit = raw_perc
            if perc_warn is not None and perc_crit is not None:
                used_perc = float(cur_depth_int) / max_depth_int * 100
                yield from check_levels(
                    used_perc,
                    label="Queue depth",
                    levels_upper=("fixed", (perc_warn, perc_crit)),
                    render_func=render.percent,
                    notice_only=True,
                )


def ibm_mq_msg_age(msg_age: str | None, params: _QueueParams) -> CheckResult:
    label = "Oldest message"
    if not msg_age:
        yield Result(state=State.OK, summary=f"{label}: n/a")
        return
    msgage_levels = params.get("msgage")
    yield from check_levels(
        int(msg_age),
        label=label,
        levels_upper=("fixed", msgage_levels) if msgage_levels else ("no_levels", None),
        metric_name="msgage",
        render_func=render.timespan,
    )


def ibm_mq_agent_timestamp(item: str, parsed: Section) -> datetime:
    qmgr_name = item.split(":", 1)[0]
    return dateutil.parser.isoparse(parsed[qmgr_name]["NOW"])


def ibm_mq_last_age(
    mq_date: str | None,
    mq_time: str | None,
    agent_timestamp: datetime,
    label: str,
    levels: tuple[int, int] | None,
) -> CheckResult:
    if not (mq_date and mq_time):
        yield Result(state=State.OK, summary=f"{label}: n/a")
        return
    mq_datetime = "{} {}".format(mq_date, mq_time.replace(".", ":"))
    input_time = dateutil.parser.parse(mq_datetime, default=agent_timestamp)
    age = abs((agent_timestamp - input_time).total_seconds())
    yield from check_levels(
        age,
        label=label,
        levels_upper=("fixed", levels) if levels else ("no_levels", None),
        render_func=render.timespan,
    )


def ibm_mq_procs(cnt: str, label: str, wato: _ProcLevels | None, metric: str) -> CheckResult:
    yield from check_levels(
        int(cnt),
        label=label,
        levels_upper=("fixed", wato["upper"]) if wato and "upper" in wato else ("no_levels", None),
        levels_lower=("fixed", wato["lower"]) if wato and "lower" in wato else ("no_levels", None),
        metric_name=metric,
        render_func=str,
    )


def ibm_mq_get_qtime(qtime: str, label: str, key: str) -> CheckResult:
    if not qtime or qtime == "999999999":
        time_in_seconds = 0.0
        info_value = "n/a"
    else:
        time_in_seconds = int(qtime) / 1000000
        info_value = render.timespan(time_in_seconds)
    yield Result(state=State.OK, summary=f"{label}: {info_value}")
    yield Metric(key, time_in_seconds)


check_plugin_ibm_mq_queues = CheckPlugin(
    name="ibm_mq_queues",
    service_name="IBM MQ Queue %s",
    discovery_function=discover_ibm_mq_queues,
    check_function=check_ibm_mq_queues,
    check_ruleset_name="ibm_mq_queues",
    check_default_parameters={},
)
