#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from pytest import MonkeyPatch

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.prism.agent_based.prism_hosts import (
    check_prism_hosts,
    CheckParamsPrimsHosts,
    discovery_prism_hosts,
)

SECTION = {
    "SRV-AHV-01": {
        "acropolis_connection_state": "kConnected",
        "block_model_name": "NX-3155G-G7",
        "boot_time_in_usecs": 1660225202040734,
        "cpu_capacity_in_hz": 51200000000,
        "cpu_frequency_in_hz": 3200000000,
        "cpu_model": "Intel(R) Xeon(R) Silver 4215R CPU @ 3.20GHz",
        "host_in_maintenance_mode": False,
        "host_maintenance_mode_reason": "life_cycle_management",
        "host_type": "HYPER_CONVERGED",
        "hypervisor_state": "kAcropolisNormal",
        "hypervisor_type": "kKvm",
        "is_degraded": False,
        "is_hardware_virtualized": False,
        "is_secure_booted": False,
        "memory_capacity_in_bytes": 404078198784,
        "name": "SRV-AHV-01",
        "num_cpu_cores": 16,
        "num_cpu_sockets": 2,
        "num_cpu_threads": 32,
        "num_vms": 4,
        "reboot_pending": False,
        "state": "NORMAL",
    },
    "SRV-AHV-02": {
        "acropolis_connection_state": "kDisconnected",
        "block_model_name": "NX-3155G-G7",
        "boot_time_in_usecs": 1660227036306217,
        "cpu_capacity_in_hz": 51200000000,
        "cpu_frequency_in_hz": 3200000000,
        "cpu_model": "Intel(R) Xeon(R) Silver 4215R CPU @ 3.20GHz",
        "host_in_maintenance_mode": False,
        "host_maintenance_mode_reason": "life_cycle_management",
        "host_type": "HYPER_CONVERGED",
        "hypervisor_state": "kAcropolisNormal",
        "hypervisor_type": "kKvm",
        "is_degraded": False,
        "is_hardware_virtualized": False,
        "is_secure_booted": False,
        "memory_capacity_in_bytes": 404078198784,
        "name": "SRV-AHV-02",
        "num_cpu_cores": 16,
        "num_cpu_sockets": 2,
        "num_cpu_threads": 32,
        "num_vms": 4,
        "reboot_pending": False,
        "state": "NORMAL",
    },
}


@pytest.mark.parametrize(
    ["section", "expected_discovery_result"],
    [
        pytest.param(
            SECTION,
            [
                Service(item="SRV-AHV-01"),
                Service(item="SRV-AHV-02"),
            ],
            id="For every host, a Service is discovered.",
        ),
    ],
)
def test_discovery_prism_hosts(
    section: Mapping[str, Any],
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discovery_prism_hosts(section)) == expected_discovery_result


@pytest.mark.parametrize(
    ["item", "params", "section", "expected_check_result"],
    [
        pytest.param(
            "SRV-AHV-01",
            {
                "system_state": "NORMAL",
                "acropolis_connection_state": True,
            },
            SECTION,
            [
                Result(state=State.OK, summary="has state NORMAL"),
                Result(state=State.OK, summary="Number of VMs 4"),
                Result(state=State.OK, summary="Memory 376 GiB"),
                Result(state=State.OK, summary="Boottime 2022-08-11 13:40:02"),
                Result(state=State.OK, summary="Acropolis state is kConnected"),
            ],
            id="If the host is connected and in the wanted state, the check is OK.",
        ),
        pytest.param(
            "SRV-AHV-01",
            {
                "system_state": "OFFLINE",
                "acropolis_connection_state": True,
            },
            SECTION,
            [
                Result(state=State.WARN, summary="has state NORMAL"),
                Result(state=State.OK, summary="expected state OFFLINE"),
                Result(state=State.OK, summary="Number of VMs 4"),
                Result(state=State.OK, summary="Memory 376 GiB"),
                Result(state=State.OK, summary="Boottime 2022-08-11 13:40:02"),
                Result(state=State.OK, summary="Acropolis state is kConnected"),
            ],
            id="If the host has not the expected state, the check is WARN.",
        ),
        pytest.param(
            "SRV-AHV-02",
            {
                "system_state": "ONLINE",
                "acropolis_connection_state": True,
            },
            SECTION,
            [
                Result(state=State.WARN, summary="has state NORMAL"),
                Result(state=State.OK, summary="expected state ONLINE"),
                Result(state=State.OK, summary="Number of VMs 4"),
                Result(state=State.OK, summary="Memory 376 GiB"),
                Result(state=State.OK, summary="Boottime 2022-08-11 14:10:36"),
                Result(state=State.CRIT, summary="Acropolis state is kDisconnected"),
            ],
            id="If the host not connected to the management, the check is CRIT.",
        ),
        pytest.param(
            "SRV-AHV-02",
            {
                "system_state": "ONLINE",
                "acropolis_connection_state": False,
            },
            SECTION,
            [
                Result(state=State.WARN, summary="has state NORMAL"),
                Result(state=State.OK, summary="expected state ONLINE"),
                Result(state=State.OK, summary="Number of VMs 4"),
                Result(state=State.OK, summary="Memory 376 GiB"),
                Result(state=State.OK, summary="Boottime 2022-08-11 14:10:36"),
                Result(state=State.OK, summary="Acropolis state is kDisconnected"),
            ],
            id="Turn off alerting.",
        ),
    ],
)
def test_check_prism_hosts(
    item: str,
    params: CheckParamsPrimsHosts,
    section: Mapping[str, Any],
    expected_check_result: Sequence[Result],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(time, "localtime", time.gmtime)
    assert (
        list(
            check_prism_hosts(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected_check_result
    )
