#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    render,
    Result,
    State,
    StringTable,
)

Section = Mapping


def parse_ceph_status(string_table: StringTable) -> Section:
    joined_lines = [" ".join(line) for line in string_table]
    section = json.loads("".join(joined_lines))

    # ceph health' JSON format has changed in luminous
    if "health" in section and "status" not in section["health"]:
        section["health"]["status"] = section["health"].get("overall_status")

    return section


def ceph_check_epoch(id_: str, epoch: float, params: Mapping[str, Any]) -> CheckResult:
    warn, crit, avg_interval_min = params.get("epoch", (None, None, 1))
    now = time.time()
    value_store = get_value_store()
    epoch_rate = get_rate(
        get_value_store(),
        f"{id_}.epoch.rate",
        now,
        epoch,
    )
    epoch_avg = get_average(value_store, f"{id_}.epoch.avg", now, epoch_rate, avg_interval_min)

    yield from check_levels_v1(
        epoch_avg,
        levels_upper=(warn, crit),
        label=f"Epoch rate ({render.timespan(avg_interval_min * 60)} average)",
    )


#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def dont_discover(section: Section) -> DiscoveryResult:
    """The plugin was replaced with the new Ceph integration in 2.4.0"""
    yield from ()


def _extract_error_messages(section: Section) -> Sequence[str]:
    error_messages = []
    for err in section.get("health", {}).get("checks", {}).values():
        err_msg = err.get("summary", {}).get("message")
        if err_msg:
            error_messages.append(err_msg)
    return sorted(error_messages)


def check_ceph_status(params: Mapping[str, Any], section: Section) -> CheckResult:
    map_health_states: dict[str, tuple[State, str]] = {
        "HEALTH_OK": (State.OK, "OK"),
        "HEALTH_WARN": (State.WARN, "warning"),
        "HEALTH_CRIT": (State.CRIT, "critical"),
        "HEALTH_ERR": (State.CRIT, "error"),
    }

    overall_status = section.get("health", {}).get("status")
    if not overall_status:
        return

    state, state_readable = map_health_states.get(
        overall_status,
        (State.UNKNOWN, "unknown[%s]" % overall_status),
    )
    if state is not State.OK:
        error_messages = _extract_error_messages(section)
        if error_messages:
            state_readable += " (%s)" % (", ".join(error_messages))

    yield Result(state=state, summary="Health: %s" % state_readable)
    yield from ceph_check_epoch("ceph_status", section["election_epoch"], params)


agent_section_ceph_status = AgentSection(
    name="ceph_status",
    parse_function=parse_ceph_status,
)


check_plugin_ceph_status = CheckPlugin(
    name="ceph_status",
    service_name="Ceph Status",
    discovery_function=dont_discover,
    check_function=check_ceph_status,
    check_default_parameters={
        "epoch": (1.0, 3.0, 30),
    },
)

# .
#   .--osds----------------------------------------------------------------.
#   |                                       _                              |
#   |                          ___  ___  __| |___                          |
#   |                         / _ \/ __|/ _` / __|                         |
#   |                        | (_) \__ \ (_| \__ \                         |
#   |                         \___/|___/\__,_|___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Suggested by customer: 50, 100 per 15 min


def check_ceph_status_osds(params: Mapping[str, Any], section: Section) -> CheckResult:
    # some instances of ceph give out osdmap data in a flat structure
    data = section["osdmap"].get("osdmap") or section["osdmap"]
    num_osds = int(data["num_osds"])
    yield from ceph_check_epoch("ceph_osds", data["epoch"], params)

    for ds, title, state in [
        ("full", "Full", State.CRIT),
        ("nearfull", "Near full", State.WARN),
    ]:
        if data.get(ds, False):
            # Return false if 'full' or 'nearfull' indicators are not in the datasets (relevant for newer ceph versions after 13.2.7)
            yield Result(state=state, summary=title)

    yield Result(
        state=State.OK,
        summary="OSDs: {}, Remapped PGs: {}".format(num_osds, data["num_remapped_pgs"]),
    )

    for ds, title, param_key in [
        ("num_in_osds", "OSDs out", "num_out_osds"),
        ("num_up_osds", "OSDs down", "num_down_osds"),
    ]:
        value = num_osds - data[ds]
        yield from check_levels_v1(
            100 * float(value) / num_osds,
            levels_upper=params.get(param_key),
            render_func=render.percent,
            label=title,
        )


check_plugin_ceph_status_osds = CheckPlugin(
    name="ceph_status_osds",
    sections=["ceph_status"],
    service_name="Ceph OSDs",
    discovery_function=dont_discover,
    check_function=check_ceph_status_osds,
    check_ruleset_name="ceph_osds",
    check_default_parameters={
        "epoch": (50.0, 100.0, 15),
        "num_out_osds": (5.0, 7.0),
        "num_down_osds": (5.0, 7.0),
    },
)

# .
#   .--pgs-----------------------------------------------------------------.
#   |                                                                      |
#   |                           _ __   __ _ ___                            |
#   |                          | '_ \ / _` / __|                           |
#   |                          | |_) | (_| \__ \                           |
#   |                          | .__/ \__, |___/                           |
#   |                          |_|    |___/                                |
#   '----------------------------------------------------------------------'


def check_ceph_status_pgs(section: Section) -> CheckResult:
    # Suggested by customer
    map_pg_states: dict[str, tuple[State, str]] = {
        "active": (State.OK, "active"),
        "backfill": (State.OK, "backfill"),
        "backfill_wait": (State.WARN, "backfill wait"),
        "backfilling": (State.WARN, "backfilling"),
        "backfill_toofull": (State.OK, "backfill too full"),
        "clean": (State.OK, "clean"),
        "creating": (State.OK, "creating"),
        "degraded": (State.WARN, "degraded"),
        "down": (State.CRIT, "down"),
        "deep": (State.OK, "deep"),
        "incomplete": (State.CRIT, "incomplete"),
        "inconsistent": (State.CRIT, "inconsistent"),
        "peered": (State.CRIT, "peered"),
        "peering": (State.OK, "peering"),
        "recovering": (State.OK, "recovering"),
        "recovery_wait": (State.OK, "recovery wait"),
        "remapped": (State.OK, "remapped"),
        "repair": (State.OK, "repair"),
        "replay": (State.WARN, "replay"),
        "scrubbing": (State.OK, "scrubbing"),
        "snaptrim": (State.OK, "snaptrim"),
        "snaptrim_wait": (State.OK, "snaptrim wait"),
        "stale": (State.CRIT, "stale"),
        "undersized": (State.OK, "undersized"),
        "wait_backfill": (State.OK, "wait backfill"),
    }

    data = section["pgmap"]
    num_pgs = data["num_pgs"]
    yield Result(state=State.OK, summary="PGs: %s" % num_pgs)

    for pgs_by_state in data["pgs_by_state"]:
        statetexts = []
        states = []
        for status in pgs_by_state["state_name"].split("+"):
            state, state_readable = map_pg_states.get(
                status, (State.UNKNOWN, "UNKNOWN[%s]" % status)
            )
            states.append(state)
            statetexts.append(state_readable)
        yield Result(
            state=State.worst(*states),
            summary="Status '{}': {}".format("+".join(statetexts), pgs_by_state["count"]),
        )


check_plugin_ceph_status_pgs = CheckPlugin(
    name="ceph_status_pgs",
    sections=["ceph_status"],
    service_name="Ceph PGs",
    discovery_function=dont_discover,
    check_function=check_ceph_status_pgs,
)

# .
#   .--mgrs----------------------------------------------------------------.
#   |                                                                      |
#   |                      _ __ ___   __ _ _ __ ___                        |
#   |                     | '_ ` _ \ / _` | '__/ __|                       |
#   |                     | | | | | | (_| | |  \__ \                       |
#   |                     |_| |_| |_|\__, |_|  |___/                       |
#   |                                |___/                                 |
#   '----------------------------------------------------------------------'


def check_ceph_status_mgrs(params: Mapping[str, Any], section: Section) -> CheckResult:
    epoch = section.get("mgrmap", {}).get("epoch")
    if epoch is None:
        return
    yield from ceph_check_epoch("ceph_mgrs", epoch, params)


check_plugin_ceph_status_mgrs = CheckPlugin(
    name="ceph_status_mgrs",
    sections=["ceph_status"],
    service_name="Ceph MGRs",
    discovery_function=dont_discover,
    check_function=check_ceph_status_mgrs,
    check_ruleset_name="ceph_mgrs",
    check_default_parameters={
        "epoch": (1.0, 2.0, 5),
    },
)
