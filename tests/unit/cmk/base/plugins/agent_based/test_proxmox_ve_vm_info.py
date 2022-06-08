#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.proxmox_ve_vm_info import (
    check_proxmox_ve_vm_info,
    parse_proxmox_ve_vm_info,
)

VM_DATA = parse_proxmox_ve_vm_info(
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
def test_check_proxmox_ve_vm_info(params, section, expected_results) -> None:
    results = tuple(check_proxmox_ve_vm_info(params, section))
    print("\n" + "\n".join(map(str, results)))
    assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    from os.path import dirname, join

    assert not pytest.main(
        [
            "--doctest-modules",
            join(
                dirname(__file__),
                "../../../../../../cmk/base/plugins/agent_based/proxmox_ve_vm_info.py",
            ),
        ]
    )
    pytest.main(["-T=unit", "-vvsx", __file__])
