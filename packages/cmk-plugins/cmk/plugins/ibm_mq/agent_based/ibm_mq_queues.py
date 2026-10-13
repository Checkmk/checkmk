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
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.ibm_mq.lib import is_ibm_mq_service_vanished, parse_ibm_mq

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


def parse_ibm_mq_queues(string_table: StringTable) -> Section:
    queue_status = parse_ibm_mq(string_table, "QSTATUS")
    queue = parse_ibm_mq(string_table, "QUEUE")
    return _merge_sections(queue, queue_status)


def _merge_sections(
    priority_section: Mapping[str, Mapping[str, str]],
    additional_section: Mapping[str, Mapping[str, str]],
) -> Mapping[str, Mapping[str, str]]:
    """Merge two queue-attribute mappings; priority_section wins on key conflicts."""
    result: dict[str, dict[str, str]] = {k: dict(v) for k, v in additional_section.items()}
    for key, value in priority_section.items():
        if key in result:
            result[key] = {**result[key], **value}
        else:
            result[key] = dict(value)
    return result


agent_section_ibm_mq_queues = AgentSection(
    name="ibm_mq_queues",
    parse_function=parse_ibm_mq_queues,
)


class _ProcLevels(TypedDict):
    upper: LevelsT[int]
    lower: LevelsT[int]


class QueueParams(TypedDict):
    curdepth: LevelsT[int]
    curdepth_perc: LevelsT[float]
    msgage: LevelsT[float]
    lgetage: LevelsT[float]
    lputage: LevelsT[float]
    ipprocs: _ProcLevels
    opprocs: _ProcLevels


DEFAULT_PARAMETERS = QueueParams(
    curdepth=("no_levels", None),
    curdepth_perc=("no_levels", None),
    msgage=("no_levels", None),
    lgetage=("no_levels", None),
    lputage=("no_levels", None),
    ipprocs={"lower": ("no_levels", None), "upper": ("no_levels", None)},
    opprocs={"lower": ("no_levels", None), "upper": ("no_levels", None)},
)


def discover_ibm_mq_queues(section: Section) -> DiscoveryResult:
    for service_name in section:
        if ":" not in service_name:
            # Do not show queue manager entry in inventory
            continue
        yield Service(item=service_name)


QTIME_PATTERN = re.compile(r"^([0-9]*),[\s]*([0-9]*)$")


def check_ibm_mq_queues(item: str, params: QueueParams, section: Section) -> CheckResult:
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
        yield from ibm_mq_last_age(mq_date, mq_time, agent_timestamp, "Last get", params["lgetage"])

    if "LPUTDATE" in data:
        mq_date = data.get("LPUTDATE")
        mq_time = data.get("LPUTTIME")
        agent_timestamp = ibm_mq_agent_timestamp(item, section)
        yield from ibm_mq_last_age(mq_date, mq_time, agent_timestamp, "Last put", params["lputage"])

    if "IPPROCS" in data:
        cnt = data["IPPROCS"]
        yield from ibm_mq_procs(cnt, "Open input handles", params["ipprocs"], "ipprocs")

    if "OPPROCS" in data:
        cnt = data["OPPROCS"]
        yield from ibm_mq_procs(cnt, "Open output handles", params["opprocs"], "opprocs")

    if "QTIME" in data:
        qtimes = data["QTIME"]
        if qtimes_match := QTIME_PATTERN.match(qtimes):
            qtime_short = qtimes_match.group(1)
            qtime_long = qtimes_match.group(2)
            yield from ibm_mq_get_qtime(qtime_short, "Qtime short", "qtime_short")
            yield from ibm_mq_get_qtime(qtime_long, "Qtime long", "qtime_long")


def ibm_mq_depth(cur_depth: str | None, max_depth: str | None, params: QueueParams) -> CheckResult:
    cur_depth_int = int(cur_depth) if cur_depth else None
    max_depth_int = int(max_depth) if max_depth else None

    val = cur_depth_int if cur_depth_int is not None else 0
    boundaries = (0, max_depth_int) if max_depth_int is not None else None

    yield from check_levels(
        val,
        label="Queue depth",
        levels_upper=params["curdepth"],
        metric_name="curdepth",
        render_func=str,
        boundaries=boundaries,
    )

    perc_levels = params["curdepth_perc"]
    if cur_depth_int and max_depth_int and perc_levels[0] != "no_levels":
        used_perc = float(cur_depth_int) / max_depth_int * 100
        yield from check_levels(
            used_perc,
            label="Queue depth",
            levels_upper=perc_levels,
            render_func=render.percent,
            notice_only=True,
        )


def ibm_mq_msg_age(msg_age: str | None, params: QueueParams) -> CheckResult:
    label = "Oldest message"
    if not msg_age:
        yield Result(state=State.OK, summary=f"{label}: n/a")
        return
    yield from check_levels(
        int(msg_age),
        label=label,
        levels_upper=params["msgage"],
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
    levels: LevelsT[float],
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
        levels_upper=levels,
        render_func=render.timespan,
    )


def ibm_mq_procs(cnt: str, label: str, levels: _ProcLevels, metric: str) -> CheckResult:
    yield from check_levels(
        int(cnt),
        label=label,
        levels_upper=levels["upper"],
        levels_lower=levels["lower"],
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
    check_default_parameters=DEFAULT_PARAMETERS,
)


def inventorize_ibm_mq_queues(section: Section) -> InventoryResult:
    for item, attrs in sorted(section.items(), key=lambda t: t[0]):
        if ":" not in item:
            # Do not show queue manager in inventory
            continue

        qmname, qname = item.split(":")
        yield TableRow(
            path=["software", "applications", "ibm_mq", "queues"],
            key_columns={
                "qmgr": qmname,
                "name": qname,
            },
            inventory_columns={
                "maxdepth": attrs["MAXDEPTH"],
                "maxmsgl": attrs.get("MAXMSGL", "n/a"),
                "created": (
                    "{} {}".format(
                        attrs.get("CRDATE", "n/a"), attrs.get("CRTIME", "").replace(".", ":")
                    )
                ).strip(),
                "altered": (
                    "{} {}".format(
                        attrs.get("ALTDATE", "n/a"), attrs.get("ALTTIME", "").replace(".", ":")
                    )
                ).strip(),
                "monq": attrs.get("MONQ", "n/a"),
            },
            status_columns={},
        )


inventory_plugin_ibm_mq_queues = InventoryPlugin(
    name="ibm_mq_queues",
    inventory_function=inventorize_ibm_mq_queues,
)
