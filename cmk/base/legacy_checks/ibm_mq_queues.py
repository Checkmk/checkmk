#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import re

import dateutil.parser

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.ibm_mq import is_ibm_mq_service_vanished

check_info = {}

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


def inventory_ibm_mq_queues(parsed):
    for service_name in parsed:
        if ":" not in service_name:
            # Do not show queue manager entry in inventory
            continue
        yield service_name, {}


QTIME_PATTERN = re.compile(r"^([0-9]*),[\s]*([0-9]*)$")


def check_ibm_mq_queues(item, params, parsed):
    if is_ibm_mq_service_vanished(item, parsed):
        return
    data = parsed[item]

    if "CURDEPTH" in data:
        cur_depth = data.get("CURDEPTH")
        max_depth = data.get("MAXDEPTH")
        yield ibm_mq_depth(cur_depth, max_depth, params)

    if "MSGAGE" in data:
        msg_age = data.get("MSGAGE")
        yield ibm_mq_msg_age(msg_age, params)

    if "LGETDATE" in data:
        mq_date = data.get("LGETDATE")
        mq_time = data.get("LGETTIME")
        agent_timestamp = ibm_mq_agent_timestamp(item, parsed)
        yield ibm_mq_last_age(mq_date, mq_time, agent_timestamp, "Last get", "lgetage", params)

    if "LPUTDATE" in data:
        mq_date = data.get("LPUTDATE")
        mq_time = data.get("LPUTTIME")
        agent_timestamp = ibm_mq_agent_timestamp(item, parsed)
        yield ibm_mq_last_age(mq_date, mq_time, agent_timestamp, "Last put", "lputage", params)

    if "IPPROCS" in data:
        cnt = data["IPPROCS"]
        yield ibm_mq_procs(cnt, "Open input handles", "ipprocs", "ipprocs", params)

    if "OPPROCS" in data:
        cnt = data["OPPROCS"]
        yield ibm_mq_procs(cnt, "Open output handles", "opprocs", "opprocs", params)

    if "QTIME" in data:
        qtimes = data["QTIME"]
        if qtimes_match := QTIME_PATTERN.match(qtimes):
            qtime_short = qtimes_match.group(1)
            qtime_long = qtimes_match.group(2)
            yield ibm_mq_get_qtime(qtime_short, "Qtime short", "qtime_short")
            yield ibm_mq_get_qtime(qtime_long, "Qtime long", "qtime_long")


def ibm_mq_depth(cur_depth, max_depth, params):
    if cur_depth:
        cur_depth = int(cur_depth)
    if max_depth:
        max_depth = int(max_depth)

    infotext = "Queue depth: %d" % cur_depth
    levelstext = []
    state = 0

    warn, crit = params.get("curdepth", (None, None))
    if warn is not None or crit is not None:
        if cur_depth >= crit:
            state = 2
        elif cur_depth >= warn:
            state = 1
        if state:
            levelstext.append("%d/%d" % (warn, crit))
    perfdata = [("curdepth", cur_depth, warn, crit, 0, max_depth)]

    if cur_depth and max_depth:
        state_perc = 0
        used_perc = float(cur_depth) / max_depth * 100
        infotext += " (%.1f%%)" % used_perc
        warn_perc, crit_perc = params.get("curdepth_perc", (None, None))
        if warn_perc is not None or crit_perc is not None:
            if used_perc >= crit_perc:
                state_perc = 2
            elif used_perc >= warn_perc:
                state_perc = 1
            if state_perc:
                levelstext.append(f"{warn_perc}%/{crit_perc}%")
            state = max(state, state_perc)

    if state:
        infotext += " (warn/crit at %s)" % " and ".join(levelstext)

    return state, infotext, perfdata


def ibm_mq_msg_age(msg_age, params):
    label = "Oldest message"
    if not msg_age:
        return (0, label + ": n/a", [])
    return check_levels(
        int(msg_age),
        "msgage",
        params.get("msgage"),
        human_readable_func=render.timespan,
        infoname=label,
    )


def ibm_mq_agent_timestamp(item, parsed):
    qmgr_name = item.split(":", 1)[0]
    now = dateutil.parser.isoparse(parsed[qmgr_name]["NOW"])
    return now


def ibm_mq_last_age(mq_date, mq_time, agent_timestamp, label, key, params):
    if not (mq_date and mq_time):
        return (0, label + ": n/a", [])
    mq_datetime = "{} {}".format(mq_date, mq_time.replace(".", ":"))
    input_time = dateutil.parser.parse(mq_datetime, default=agent_timestamp)
    age = (agent_timestamp - input_time).total_seconds()
    return check_levels(
        age, None, params.get(key), human_readable_func=render.timespan, infoname=label
    )


def ibm_mq_procs(cnt, label, levels_key, metric, params):
    wato = params.get(levels_key)
    levels = tuple()
    if wato:
        levels += wato.get("upper", (None, None))
        levels += wato.get("lower", (None, None))
    return check_levels(int(cnt), metric, levels, human_readable_func=int, infoname=label)


def ibm_mq_get_qtime(qtime, label, key):
    if not qtime or qtime == "999999999":
        time_in_seconds = 0.0
        info_value = "n/a"
    else:
        time_in_seconds = int(qtime) / 1000000
        info_value = render.timespan(time_in_seconds)
    infotext = f"{label}: {info_value}"
    perfdata = [(key, time_in_seconds, None, None)]
    return (0, infotext, perfdata)


check_info["ibm_mq_queues"] = LegacyCheckDefinition(
    name="ibm_mq_queues",
    service_name="IBM MQ Queue %s",
    discovery_function=inventory_ibm_mq_queues,
    check_function=check_ibm_mq_queues,
    check_ruleset_name="ibm_mq_queues",
    check_default_parameters={},
)
