#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

import cmk.plugins.proxmox_ve.agent_based.proxmox_ve_vm_info as pvvi
from cmk.agent_based.v2 import CheckResult, Result, State

VM_DATA = pvvi.parse_proxmox_ve_vm_info(
    [
        [
            json.dumps(
                {
                    "name": "aq-test.lan.mathias-kettner.de",
                    "node": "pve-dc4-001",
                    "status": "running",
                    "type": "qemu",
                    "vmid": "133",
                }
            )
        ]
    ]
)


@pytest.mark.parametrize(
    "params,section,expected_results",
    [
        (
            {},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.OK, summary="Status: running"),
                Result(state=State.OK, summary="Type: qemu"),
                Result(state=State.OK, summary="Host: pve-dc4-001"),
            ),
        ),
        (
            {"required_vm_status": "idle"},
            VM_DATA,
            (
                Result(state=State.OK, summary="VM ID: 133"),
                Result(state=State.WARN, summary="Status: running (required: idle)"),
                Result(state=State.OK, summary="Type: qemu"),
                Result(state=State.OK, summary="Host: pve-dc4-001"),
            ),
        ),
    ],
)
def test_check_proxmox_ve_vm_info(
    params: Mapping[str, object], section: pvvi.Section, expected_results: CheckResult
) -> None:
    results = tuple(pvvi.check_proxmox_ve_vm_info(params, section))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    assert not pytest.main(["--doctest-modules", pvvi.__file__])
    pytest.main(["-T=unit", "-vvsx", __file__])
