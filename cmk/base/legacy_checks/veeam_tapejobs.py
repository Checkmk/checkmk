#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_value_store, render

check_info = {}

BACKUP_STATE = {"Success": 0, "Warning": 1, "Failed": 2}

_DAY = 3600 * 24


def parse_veeam_tapejobs(string_table):
    parsed = {}
    columns = [s.lower() for s in string_table[0]]

    for line in string_table[1:]:
        if len(line) < len(columns):
            continue

        name = " ".join(line[: -(len(columns) - 1)])
        job_id, last_result, last_state = line[-(len(columns) - 1) :]
        parsed[name] = {
            "job_id": job_id,
            "last_result": last_result,
            "last_state": last_state,
        }

    return parsed


def discover_veeam_tapejobs(parsed):
    for job in parsed:
        yield job, {}


def check_veeam_tapejobs(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    value_store = get_value_store()
    job_id = data["job_id"]
    last_result = data["last_result"]
    last_state = data["last_state"]

    if last_result != "None" or last_state not in ("Working", "Idle"):
        yield BACKUP_STATE.get(last_result, 2), "Last backup result: %s" % last_result
        yield 0, "Last state: %s" % last_state
        value_store[f"{job_id}.running_since"] = None
        return

    running_since = value_store.get(f"{job_id}.running_since")
    now = time.time()
    if not running_since:
        running_since = now
        value_store[f"{job_id}.running_since"] = now
    running_time = now - running_since

    yield (
        0,
        f"Backup in progress since {render.datetime(running_since)} (currently {last_state.lower()})",
    )
    yield check_levels(
        running_time,
        None,
        params["levels_upper"],
        human_readable_func=render.timespan,
        infoname="Running time",
    )


check_info["veeam_tapejobs"] = LegacyCheckDefinition(
    name="veeam_tapejobs",
    parse_function=parse_veeam_tapejobs,
    service_name="VEEAM Tape Job %s",
    discovery_function=discover_veeam_tapejobs,
    check_function=check_veeam_tapejobs,
    check_ruleset_name="veeam_tapejobs",
    check_default_parameters={
        "levels_upper": (1 * _DAY, 2 * _DAY),
    },
)
