#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Result, State
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_name
from cmk.plugins.vsphere.lib.esx_vsphere import SectionESXVm


def test_parse_esx_vsphere_name() -> None:
    name = esx_vsphere_vm.parse_esx_vm_name({"name": ["scwagprc01.widag.local"]})
    assert name == "scwagprc01.widag.local"


def test_check_name() -> None:
    section = SectionESXVm(
        mounted_devices=(),
        snapshots=(),
        status=None,
        power_state=None,
        memory=None,
        cpu=None,
        datastores=(),
        heartbeat=None,
        host=None,
        name=(name := "host"),
        systime=None,
    )
    check_result = list(esx_vsphere_vm_name.check_name(section))
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].state == State.OK
    assert results[0].summary == name


def test_check_name_missing() -> None:
    section = SectionESXVm(
        mounted_devices=(),
        snapshots=(),
        status=None,
        power_state=None,
        memory=None,
        cpu=None,
        datastores=(),
        heartbeat=None,
        host=None,
        name=None,
        systime=None,
    )
    with pytest.raises(IgnoreResultsError):
        list(esx_vsphere_vm_name.check_name(section))
