#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from tests.unit.cmk.plugins.vsphere.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.agent_based.v2 import Result, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_guest_tools
from cmk.plugins.vsphere.lib.esx_vsphere import ESXStatus, SectionESXVm


def test_parse_esx_vsphere_guest_tools() -> None:
    status = esx_vsphere_vm._parse_vm_status({"guest.toolsVersionStatus": ["guestToolsUnmanaged"]})
    assert status == ESXStatus.guestToolsUnmanaged


@pytest.mark.parametrize(
    "vm_status, check_state",
    [
        (ESXStatus.guestToolsCurrent, State.OK),
        (ESXStatus.guestToolsNeedUpgrade, State.WARN),
        (ESXStatus.guestToolsNotInstalled, State.CRIT),
        (ESXStatus.guestToolsUnmanaged, State.OK),
    ],
)
def test_check_guest_tools(vm_status: ESXStatus, check_state: State) -> None:
    check_result = list(
        esx_vsphere_vm_guest_tools.check_guest_tools(
            esx_vsphere_vm_guest_tools.CHECK_DEFAULT_PARAMETERS, _esx_vm_section(vm_status)
        )
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == check_state


def test_check_guest_tools_with_unknonw() -> None:
    check_result = list(esx_vsphere_vm_guest_tools.check_guest_tools({}, _esx_vm_section(None)))
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.UNKNOWN


def test_check_guest_tools_with_params() -> None:
    check_result = list(
        esx_vsphere_vm_guest_tools.check_guest_tools(
            {"guestToolsNeedUpgrade": 0}, _esx_vm_section(ESXStatus.guestToolsNeedUpgrade)
        )
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.OK


def _esx_vm_section(status: ESXStatus | None) -> SectionESXVm:
    return esx_vm_section(status=status)
