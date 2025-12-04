#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime

import pytest

from cmk.agent_based.v2 import CheckResult, FixedLevelsT, Metric, NoLevelsT, Result, State
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_info import (
    _check_days_until_expiration,
    check_proxmox_ve_node_info,
    Params,
    parse_proxmox_ve_node_info,
)
from cmk.plugins.proxmox_ve.lib.node_info import SectionNodeInfo

NODE_DATA = parse_proxmox_ve_node_info(
    [
        [
            json.dumps(
                {
                    "lxc": ["103", "101", "108", "105", "104"],
                    "version": "6.2-15",
                    "qemu": ["102", "9000", "106", "109"],
                    "status": "online",
                    "subscription": {
                        "nextduedate": "2021-07-03",
                        "status": "active",
                    },
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        pytest.param(
            {
                "required_node_status": {"active": 0, "offline": 1, "unknown": 1},
                "required_subscription_status": {"new": 0, "active": 0},
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            NODE_DATA,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.OK, summary="Subscription: active"),
                Result(state=State.OK, summary="Version: 6.2-15"),
                Result(state=State.OK, summary="Hosted VMs: 5x LXC, 4x Qemu"),
            ],
            id="All OK -> both as required",
        ),
        pytest.param(
            {
                "required_node_status": {"offline": 0, "online": 1, "unknown": 1},
                "required_subscription_status": {"inactive": 0, "active": 1},
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            NODE_DATA,
            [
                Result(state=State.WARN, summary="Status: online"),
                Result(state=State.WARN, summary="Subscription: active"),
                Result(state=State.OK, summary="Version: 6.2-15"),
                Result(state=State.OK, summary="Hosted VMs: 5x LXC, 4x Qemu"),
            ],
            id="All WARN -> both not as required",
        ),
        pytest.param(
            {
                "subscription_expiration_days_levels": ("fixed", (30, 7)),
            },
            NODE_DATA,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.OK, summary="Subscription: active"),
                Result(state=State.OK, summary="Version: 6.2-15"),
                Result(state=State.OK, summary="Hosted VMs: 5x LXC, 4x Qemu"),
            ],
            id="All OK -> no params given",
        ),
    ],
)
def test_check_proxmox_ve_node_info(
    params: Params, section: SectionNodeInfo, expected_results: CheckResult
) -> None:
    assert list(check_proxmox_ve_node_info(params, section)) == expected_results


@pytest.mark.parametrize(
    "expiration_days_levels,expiration_date_str,expected_results",
    [
        pytest.param(
            ("no_levels", None),
            "2021-09-02",
            [
                Result(state=State.OK, summary="Subscription expiration in: 64 days"),
                Metric("days_until_subscription_expiration", 64.0),
            ],
            id="OK -> no levels",
        ),
        pytest.param(
            ("fixed", (30, 7)),
            "2021-09-02",
            [
                Result(state=State.OK, summary="Subscription expiration in: 64 days"),
                Metric("days_until_subscription_expiration", 64.0, boundaries=(30.0, 7.0)),
            ],
            id="OK -> expiration more than 30 days away",
        ),
        pytest.param(
            ("fixed", (30, 7)),
            "2021-07-03",
            [
                Result(
                    state=State.CRIT,
                    summary="Subscription expiration in: 3 days (warn/crit below 30 days/7 days)",
                ),
                Metric("days_until_subscription_expiration", 3.0, boundaries=(30.0, 7.0)),
            ],
            id="CRIT -> expiration less than 7 days away",
        ),
    ],
)
def test_check_days_until_expiration(
    expiration_days_levels: NoLevelsT | FixedLevelsT[int],
    expiration_date_str: str,
    expected_results: CheckResult,
) -> None:
    assert (
        list(
            _check_days_until_expiration(
                expiration_days_levels=expiration_days_levels,
                expiration_date_str=expiration_date_str,
                now=datetime(2021, 6, 30),
            )
        )
        == expected_results
    )
