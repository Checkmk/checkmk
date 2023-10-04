#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import time

from cmk.base.check_api import (
    check_levels,
    get_age_human_readable,
    LegacyCheckDefinition,
    state_markers,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_average,
    get_rate,
    get_value_store,
    render,
)


def parse_ceph_status(string_table):
    joined_lines = [" ".join(line) for line in string_table]
    parsed = json.loads("".join(joined_lines))

    # ceph health' JSON format has changed in luminous
    if "health" in parsed and "status" not in parsed["health"]:
        parsed["health"]["status"] = parsed["health"].get("overall_status")

    return parsed


def ceph_check_epoch(id_, epoch, params):
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

    infoname = "Epoch rate (%s average)" % get_age_human_readable(avg_interval_min * 60)
    return check_levels(
        epoch_avg,
        None,
        (warn, crit),
        infoname=infoname,
    )[:2]


#   .--status--------------------------------------------------------------.
#   |                         _        _                                   |
#   |                     ___| |_ __ _| |_ _   _ ___                       |
#   |                    / __| __/ _` | __| | | / __|                      |
#   |                    \__ \ || (_| | |_| |_| \__ \                      |
#   |                    |___/\__\__,_|\__|\__,_|___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Suggested by customer: 1,3 per 30 min


def inventory_ceph_status(parsed):
    return [(None, {})]


def _extract_error_messages(parsed):
    error_messages = []
    for err in parsed.get("health", {}).get("checks", {}).values():
        err_msg = err.get("summary", {}).get("message")
        if err_msg:
            error_messages.append(err_msg)
    return sorted(error_messages)


# TODO genereller Status -> ceph health (Ausnahmen für "too many PGs per OSD" als Option ermöglichen)
def check_ceph_status(_no_item, params, parsed):
    map_health_states = {
        "HEALTH_OK": (0, "OK"),
        "HEALTH_WARN": (1, "warning"),
        "HEALTH_CRIT": (2, "critical"),
        "HEALTH_ERR": (2, "error"),
    }

    overall_status = parsed.get("health", {}).get("status")
    if not overall_status:
        return

    state, state_readable = map_health_states.get(
        overall_status,
        (3, "unknown[%s]" % overall_status),
    )
    if state:
        error_messages = _extract_error_messages(parsed)
        if error_messages:
            state_readable += " (%s)" % (", ".join(error_messages))

    yield state, "Health: %s" % state_readable
    yield ceph_check_epoch("ceph_status", parsed["election_epoch"], params)


check_info["ceph_status"] = LegacyCheckDefinition(
    parse_function=parse_ceph_status,
    service_name="Ceph Status",
    discovery_function=inventory_ceph_status,
    check_function=check_ceph_status,
    check_default_parameters={
        "epoch": (1, 3, 30),
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


def inventory_ceph_status_osds(parsed):
    if "osdmap" in parsed:
        return [(None, {})]
    return []


def check_ceph_status_osds(_no_item, params, parsed):
    # some instances of ceph give out osdmap data in a flat structure
    data = parsed["osdmap"].get("osdmap") or parsed["osdmap"]
    num_osds = int(data["num_osds"])
    yield ceph_check_epoch("ceph_osds", data["epoch"], params)

    for ds, title, state in [
        ("full", "Full", 2),
        ("nearfull", "Near full", 1),
    ]:
        if data.get(ds, False):
            # Return false if 'full' or 'nearfull' indicators are not in the datasets (relevant for newer ceph versions after 13.2.7)
            yield state, title

    yield 0, "OSDs: {}, Remapped PGs: {}".format(num_osds, data["num_remapped_pgs"])

    for ds, title, param_key in [
        ("num_in_osds", "OSDs out", "num_out_osds"),
        ("num_up_osds", "OSDs down", "num_down_osds"),
    ]:
        state = 0
        value = num_osds - data[ds]
        value_perc = 100 * float(value) / num_osds
        infotext = f"{title}: {value}, {render.percent(value_perc)}"
        if params.get(param_key):
            warn, crit = params[param_key]
            if value_perc >= crit:
                state = 2
            elif value_perc >= warn:
                state = 1
            if state > 0:
                infotext += " (warn/crit at {}/{})".format(
                    render.percent(warn),
                    render.percent(crit),
                )

        yield state, infotext


check_info["ceph_status.osds"] = LegacyCheckDefinition(
    service_name="Ceph OSDs",
    sections=["ceph_status"],
    discovery_function=inventory_ceph_status_osds,
    check_function=check_ceph_status_osds,
    check_ruleset_name="ceph_osds",
    check_default_parameters={
        "epoch": (50, 100, 15),
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


def inventory_ceph_status_pgs(parsed):
    if "pgmap" in parsed:
        return [(None, {})]
    return []


def check_ceph_status_pgs(_no_item, params, parsed):
    # Suggested by customer
    map_pg_states = {
        "active": (0, "active"),
        "backfill": (0, "backfill"),
        "backfill_wait": (1, "backfill wait"),
        "backfilling": (1, "backfilling"),
        "backfill_toofull": (0, "backfill too full"),
        "clean": (0, "clean"),
        "creating": (0, "creating"),
        "degraded": (1, "degraded"),
        "down": (2, "down"),
        "deep": (0, "deep"),
        "incomplete": (2, "incomplete"),
        "inconsistent": (2, "inconsistent"),
        "peered": (2, "peered"),
        "peering": (0, "peering"),
        "recovering": (0, "recovering"),
        "recovery_wait": (0, "recovery wait"),
        "remapped": (0, "remapped"),
        "repair": (0, "repair"),
        "replay": (1, "replay"),
        "scrubbing": (0, "scrubbing"),
        "snaptrim": (0, "snaptrim"),
        "snaptrim_wait": (0, "snaptrim wait"),
        "stale": (2, "stale"),
        "undersized": (0, "undersized"),
        "wait_backfill": (0, "wait backfill"),
    }

    data = parsed["pgmap"]
    num_pgs = data["num_pgs"]
    pgs_info = "PGs: %s" % num_pgs
    states = [0]
    infotexts = []

    for pgs_by_state in data["pgs_by_state"]:
        statetexts = []
        for status in pgs_by_state["state_name"].split("+"):
            state, state_readable = map_pg_states.get(status, (3, "UNKNOWN[%s]" % status))
            states.append(state)
            statetexts.append(f"{state_readable}{state_markers[state]}")
        infotexts.append("Status '{}': {}".format("+".join(statetexts), pgs_by_state["count"]))

    return max(states), "{}, {}".format(pgs_info, ", ".join(infotexts))


check_info["ceph_status.pgs"] = LegacyCheckDefinition(
    service_name="Ceph PGs",
    sections=["ceph_status"],
    discovery_function=inventory_ceph_status_pgs,
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

# Suggested by customer: 1, 2 per 5 min


def inventory_ceph_status_mgrs(parsed):
    if "epoch" in parsed.get("mgrmap", {}):
        return [(None, {})]
    return []


def check_ceph_status_mgrs(_no_item, params, parsed):
    epoch = parsed.get("mgrmap", {}).get("epoch")
    if epoch is None:
        return
    yield ceph_check_epoch("ceph_mgrs", epoch, params)


check_info["ceph_status.mgrs"] = LegacyCheckDefinition(
    service_name="Ceph MGRs",
    sections=["ceph_status"],
    discovery_function=inventory_ceph_status_mgrs,
    check_function=check_ceph_status_mgrs,
    check_ruleset_name="ceph_mgrs",
    check_default_parameters={
        "epoch": (1, 2, 5),
    },
)
