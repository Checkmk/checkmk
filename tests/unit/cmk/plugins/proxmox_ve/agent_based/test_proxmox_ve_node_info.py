#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_node_info as pvni
from cmk.agent_based.v2 import CheckResult, Result, State

NODE_DATA = pvni.parse_proxmox_ve_node_info(
    [
        [
            json.dumps(
                {
                    "lxc": ["103", "101", "108", "105", "104"],
                    "proxmox_ve_version": {
                        "release": "6.2",
                        "repoid": "48bd51b6",
                        "version": "6.2-15",
                    },
                    "qemu": ["102", "9000", "106", "109"],
                    "status": "online",
                    "subscription": {
                        "checktime": "1607143921",
                        "key": "pve2c-be9cadf297",
                        "level": "c",
                        "nextduedate": "2021-07-03",
                        "productname": "Proxmox VE Community Subscription 2 CPUs/year",
                        "regdate": "2020-07-03 00:00:00",
                        "status": "Active",
                    },
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        (
            {},  # must be explicitly set, evaluates to (0.,0.)
            NODE_DATA,
            (
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.OK, summary="Subscription: active"),
                Result(state=State.OK, summary="Version: 6.2-15"),
                Result(state=State.OK, summary="Hosted VMs: 5x LXC, 4x Qemu"),
            ),
        ),
        (
            {
                "required_node_status": "online",
                "required_subscription_status": "active",
            },
            NODE_DATA,
            (
                Result(state=State.OK, summary="Status: online (required: online)"),
                Result(state=State.OK, summary="Subscription: active (required: active)"),
                Result(state=State.OK, summary="Version: 6.2-15"),
                Result(state=State.OK, summary="Hosted VMs: 5x LXC, 4x Qemu"),
            ),
        ),
        (
            {
                "required_node_status": "offline",
                "required_subscription_status": "Inactive",
            },
            NODE_DATA,
            (
                Result(state=State.WARN, summary="Status: online (required: offline)"),
                Result(state=State.WARN, summary="Subscription: active (required: inactive)"),
                Result(state=State.OK, summary="Version: 6.2-15"),
                Result(state=State.OK, summary="Hosted VMs: 5x LXC, 4x Qemu"),
            ),
        ),
    ],
)
def test_check_proxmox_ve_node_info(
    params: Mapping[str, object], section: pvni.Section, expected_results: CheckResult
) -> None:
    results = tuple(pvni.check_proxmox_ve_node_info(params, section))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    assert not pytest.main(["--doctest-modules", pvni.__file__])
    pytest.main(["-vvsx", __file__])
