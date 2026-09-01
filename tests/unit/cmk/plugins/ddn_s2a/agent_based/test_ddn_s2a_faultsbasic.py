#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.ddn_s2a.agent_based.ddn_s2a_faultsbasic import (
    check_ddn_s2a_faultsbasic,
    check_ddn_s2a_faultsbasic_bootstatus,
    check_ddn_s2a_faultsbasic_cachecoh,
    check_ddn_s2a_faultsbasic_disks,
    check_ddn_s2a_faultsbasic_dualcomm,
    check_ddn_s2a_faultsbasic_ethernet,
    check_ddn_s2a_faultsbasic_fans,
    check_ddn_s2a_faultsbasic_pingfault,
    check_ddn_s2a_faultsbasic_ps,
    check_ddn_s2a_faultsbasic_temp,
    discover_ddn_s2a_faultsbasic,
    discover_ddn_s2a_faultsbasic_disks,
    parse_ddn_s2a_faultsbasic,
)

# The API only reports the "failure" fields (cache coherency, dual communication,
# ethernet) in case of a failure, so they are absent here.
_HEALTHY_RESPONSE = (
    "0@18@disk_failures_count@0@avr_temp_C_failures_count@0"
    "@avr_temp_W_failures_count@0@avr_pwr_sup_failures_count@0"
    "@avr_fan_ctrl_failures_count@0@ping_fault@FALSE@system_fully_booted@TRUE"
    "@hstd1_online_failure@FALSE@hstd2_online_failure@FALSE@$"
)

_FAULTY_RESPONSE = (
    "0@40@disk_failures_count@2@failed_disk_item@1A@failed_disk_item@2B"
    "@avr_temp_C_failures_count@1@avr_temp_W_failures_count@2"
    "@failed_avr_temp_C_item@Unit 1@failed_avr_temp_W_item@Unit 2"
    "@avr_pwr_sup_failures_count@1@failed_avr_pwr_sup_item@PSU 1"
    "@avr_fan_ctrl_failures_count@1@failed_avr_fan_ctrl_item@Fan 3 failed"
    "@ping_fault@TRUE@ping_fault_tag@no response@system_fully_booted@FALSE"
    "@cache_coherency@not established@dual_comm_established@FALSE"
    "@ethernet_working@not working@hstd1_online_failure@TRUE"
    "@hstd1_online_status@Restarting@hstd2_online_failure@TRUE"
    "@hstd2_online_status@Failed@$"
)

_HEALTHY = parse_ddn_s2a_faultsbasic([[_HEALTHY_RESPONSE]])
_FAULTY = parse_ddn_s2a_faultsbasic([[_FAULTY_RESPONSE]])


def test_discover_ddn_s2a_faultsbasic_units() -> None:
    assert list(discover_ddn_s2a_faultsbasic(_HEALTHY)) == [
        Service(item="1"),
        Service(item="2"),
    ]


def test_discover_ddn_s2a_faultsbasic_subcheck() -> None:
    assert list(discover_ddn_s2a_faultsbasic_disks(_HEALTHY)) == [Service()]
    assert not list(discover_ddn_s2a_faultsbasic_disks(parse_ddn_s2a_faultsbasic([["0@0@$"]])))


def test_check_ddn_s2a_faultsbasic_disks() -> None:
    params = {"levels": (1, 2)}
    assert list(check_ddn_s2a_faultsbasic_disks(params, _HEALTHY)) == [
        Result(state=State.OK, summary="Failures detected: 0"),
    ]
    assert list(check_ddn_s2a_faultsbasic_disks(params, _FAULTY)) == [
        Result(state=State.CRIT, summary="Failures detected: 2 (warn/crit at 1/2)"),
        Result(state=State.OK, summary="Failed disks: 1A, 2B"),
    ]


def test_check_ddn_s2a_faultsbasic_temp() -> None:
    assert list(check_ddn_s2a_faultsbasic_temp(_HEALTHY)) == [
        Result(state=State.OK, summary="0 critical failures, 0 warnings"),
    ]
    assert list(check_ddn_s2a_faultsbasic_temp(_FAULTY)) == [
        Result(
            state=State.CRIT,
            summary=(
                "1 critical failures, 2 warnings. Critical failures: Unit 1. Warnings: Unit 2"
            ),
        ),
    ]


def test_check_ddn_s2a_faultsbasic_ps() -> None:
    assert list(check_ddn_s2a_faultsbasic_ps(_HEALTHY)) == [
        Result(state=State.OK, summary="No power supply failures detected"),
    ]
    assert list(check_ddn_s2a_faultsbasic_ps(_FAULTY)) == [
        Result(state=State.CRIT, summary="Power supply failure: PSU 1"),
    ]


def test_check_ddn_s2a_faultsbasic_fans() -> None:
    params = {"levels": (1, 2)}
    assert list(check_ddn_s2a_faultsbasic_fans(params, _HEALTHY)) == [
        Result(state=State.OK, summary="Detected fan failures: 0"),
    ]
    assert list(check_ddn_s2a_faultsbasic_fans(params, _FAULTY)) == [
        Result(state=State.WARN, summary="Detected fan failures: 1 (warn/crit at 1/2)"),
        Result(state=State.OK, summary="Fan 3 failed"),
    ]


def test_check_ddn_s2a_faultsbasic_pingfault() -> None:
    assert list(check_ddn_s2a_faultsbasic_pingfault(_HEALTHY)) == [
        Result(state=State.OK, summary="No fault detected"),
    ]
    assert list(check_ddn_s2a_faultsbasic_pingfault(_FAULTY)) == [
        Result(state=State.WARN, summary="Ping Fault: no response"),
    ]


def test_check_ddn_s2a_faultsbasic_bootstatus() -> None:
    assert list(check_ddn_s2a_faultsbasic_bootstatus(_HEALTHY)) == [
        Result(state=State.OK, summary="System fully booted"),
    ]
    assert list(check_ddn_s2a_faultsbasic_bootstatus(_FAULTY)) == [
        Result(state=State.WARN, summary="System not fully booted"),
    ]


def test_check_ddn_s2a_faultsbasic_cachecoh() -> None:
    assert list(check_ddn_s2a_faultsbasic_cachecoh(_HEALTHY)) == [
        Result(state=State.OK, summary="Cache coherency: established"),
    ]
    assert list(check_ddn_s2a_faultsbasic_cachecoh(_FAULTY)) == [
        Result(state=State.CRIT, summary="Cache coherency: not established"),
    ]


def test_check_ddn_s2a_faultsbasic_dualcomm() -> None:
    assert list(check_ddn_s2a_faultsbasic_dualcomm(_HEALTHY)) == [
        Result(state=State.OK, summary="Dual comm established"),
    ]
    assert list(check_ddn_s2a_faultsbasic_dualcomm(_FAULTY)) == [
        Result(state=State.CRIT, summary="Dual comm not established"),
    ]


def test_check_ddn_s2a_faultsbasic_ethernet() -> None:
    assert list(check_ddn_s2a_faultsbasic_ethernet(_HEALTHY)) == [
        Result(state=State.OK, summary="Ethernet connection established"),
    ]
    assert list(check_ddn_s2a_faultsbasic_ethernet(_FAULTY)) == [
        Result(state=State.WARN, summary="Ethernet not working"),
    ]


def test_check_ddn_s2a_faultsbasic_units() -> None:
    assert list(check_ddn_s2a_faultsbasic("1", _HEALTHY)) == [
        Result(state=State.OK, summary="No failure detected"),
    ]
    # A restarting unit is only a warning, any other failure is critical.
    assert list(check_ddn_s2a_faultsbasic("1", _FAULTY)) == [
        Result(state=State.WARN, summary="Unit Restarting"),
    ]
    assert list(check_ddn_s2a_faultsbasic("2", _FAULTY)) == [
        Result(state=State.CRIT, summary="Failure detected - Online status: Failed"),
    ]
