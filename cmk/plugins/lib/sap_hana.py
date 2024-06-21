#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.agent_based.v2 import IgnoreResults, Metric, Result, State, StringTable


class CheckResults(NamedTuple):
    overall_state: State
    results: list[IgnoreResults | Metric | Result] = []


ParsedSection = dict[str, dict]


def parse_sap_hana(info: StringTable) -> dict[str, StringTable]:
    parsed: dict[str, StringTable] = {}
    instance = None
    for line in info:
        joined_line = " ".join(line)
        if joined_line.startswith("[[") and joined_line.endswith("]]"):
            instance = parsed.setdefault(joined_line[2:-2], [])
        elif instance is not None:
            instance.append([e.strip('"') for e in line])
    return parsed


def get_replication_state(raw: str) -> tuple[State, str, str]:
    match raw:
        case "0":
            return State.UNKNOWN, "unknown status from replication script", "state_unknown"
        case "10":
            return State.CRIT, "no system replication", "state_no_replication"
        case "11":
            return State.CRIT, "error", "state_error"
        case "12":
            # "12" actually stands for "unknown replication status", but as per customer's information
            # (see SUP-1436), this should be indicated as "passive" replication aka secondary SAP HANA node.
            return State.OK, "passive", "state_replication_unknown"
        case "13":
            return State.WARN, "initializing", "state_initializing"
        case "14":
            return State.OK, "syncing", "state_syncing"
        case "15":
            return State.OK, "active", "state_active"

    return State.UNKNOWN, "unknown[%s]" % raw, "state_unknown"
