#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_running_on


def test_check_running_on_host() -> None:
    assert (section := esx_vsphere_vm.parse_esx_vsphere_vm([["runtime.host", "my.host.tld"]]))
    check_result = list(esx_vsphere_vm_running_on.check_running_on(section))
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.OK
    assert results[0].summary == "Running on my.host.tld"


def test_check_running_on_host_missing() -> None:
    assert (section := esx_vsphere_vm.parse_esx_vsphere_vm([]))
    check_result = list(esx_vsphere_vm_running_on.check_running_on(section))
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.UNKNOWN
    assert results[0].summary == "Runtime host information is missing"
