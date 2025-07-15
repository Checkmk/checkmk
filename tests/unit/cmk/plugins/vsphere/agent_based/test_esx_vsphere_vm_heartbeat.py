#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from tests.unit.cmk.plugins.vsphere.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.agent_based.v2 import Result, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_heartbeat
from cmk.plugins.vsphere.lib.esx_vsphere import HeartBeat, HeartBeatStatus, SectionESXVm


def test_parse_esx_vsphere_heartbeat():
    parsed_section = esx_vsphere_vm._parse_esx_vm_heartbeat_status(
        {"guestHeartbeatStatus": ["green"]}
    )
    assert parsed_section == HeartBeat(status=HeartBeatStatus.GREEN, value="green")


class HeartBeatFactory(ModelFactory):
    __model__ = HeartBeat


@pytest.mark.parametrize(
    "vm_status, check_state", [("green", State.OK), ("red", State.CRIT), ("yellow", State.WARN)]
)
def testcheck_heartbeat(vm_status: str, check_state: State) -> None:
    heartbeat = HeartBeatFactory.build(status=HeartBeatStatus(vm_status.upper()), value=vm_status)
    check_result = list(
        esx_vsphere_vm_heartbeat.check_heartbeat(
            esx_vsphere_vm_heartbeat.CHECK_DEFAULT_PARAMETERS, _esx_vm_section(heartbeat)
        )
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == check_state
    assert results[0].summary.startswith("Heartbeat status is")


def testcheck_heartbeat_gray() -> None:
    heartbeat = HeartBeatFactory.build(status=HeartBeatStatus.GRAY, value="gray")
    check_result = list(
        esx_vsphere_vm_heartbeat.check_heartbeat(
            esx_vsphere_vm_heartbeat.CHECK_DEFAULT_PARAMETERS, _esx_vm_section(heartbeat)
        )
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.WARN
    assert results[0].summary == "No VMware Tools installed, outdated or not running"


@pytest.mark.parametrize(
    "vm_status, params_key",
    [
        (HeartBeatStatus.GRAY, "heartbeat_no_tools"),
        (HeartBeatStatus.GREEN, "heartbeat_ok"),
        (HeartBeatStatus.RED, "heartbeat_missing"),
        (HeartBeatStatus.YELLOW, "heartbeat_intermittend"),
    ],
)
def testcheck_heartbeat_params(vm_status: HeartBeatStatus, params_key: str) -> None:
    heartbeat = HeartBeatFactory.build(status=vm_status)
    check_result = list(
        esx_vsphere_vm_heartbeat.check_heartbeat({params_key: 0}, _esx_vm_section(heartbeat))
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.OK


def _esx_vm_section(heartbeat: HeartBeat) -> SectionESXVm:
    return esx_vm_section(heartbeat=heartbeat)
