#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.unit.cmk.plugins.vsphere.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.agent_based.v2 import Result, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_running_on
from cmk.plugins.vsphere.lib.esx_vsphere import SectionESXVm


def test_parse_esx_vsphere_running_on_host():
    host = esx_vsphere_vm._parse_esx_vm_running_on_host(
        {"runtime.host": ["zh1wagesx02.widag.local"]}
    )
    assert host == "zh1wagesx02.widag.local"


def test_check_running_on_host() -> None:
    running_on_host = "host"
    check_result = list(
        esx_vsphere_vm_running_on.check_running_on(_esx_vm_section(running_on_host))
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.OK
    assert results[0].summary == "Running on host"


def test_check_running_on_host_missing() -> None:
    running_on_host = None
    check_result = list(
        esx_vsphere_vm_running_on.check_running_on(_esx_vm_section(running_on_host))
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.UNKNOWN
    assert results[0].summary == "Runtime host information is missing"


def _esx_vm_section(host: str | None) -> SectionESXVm:
    return esx_vm_section(host=host)
