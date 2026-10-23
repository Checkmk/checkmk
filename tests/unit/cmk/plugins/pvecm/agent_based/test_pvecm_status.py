#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, State
from cmk.plugins.pvecm.agent_based.pvecm_status import check_pvecm_status, parse_pvecm_status


def test_check_pvecm_status_reports_missing_cluster_data() -> None:
    # The section only holds a message without "key: value" pairs.
    section = parse_pvecm_status([["Cannot initialize CMAP service"]])
    assert list(check_pvecm_status(section)) == [
        Result(
            state=State.CRIT,
            summary="Cluster state unavailable: Cannot initialize CMAP service",
            details="Missing in agent output: nodes, quorum, expected votes, total votes",
        )
    ]


def test_check_pvecm_status_reports_agent_error() -> None:
    section = parse_pvecm_status([["Error", " Corosync config does not exist"]])
    assert list(check_pvecm_status(section)) == [
        Result(
            state=State.CRIT,
            summary="Cluster state unavailable: Corosync config does not exist",
            details="Missing in agent output: nodes, quorum, expected votes, total votes",
        )
    ]
