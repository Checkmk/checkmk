#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic_factories import ModelFactory

from tests.unit.cmk.base.plugins.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.base.plugins.agent_based import esx_vsphere_vm, esx_vsphere_vm_mem_usage
from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError, Metric, Result
from cmk.base.plugins.agent_based.utils import esx_vsphere


def test_parse_esx_vsphere_memory():
    parsed_section = esx_vsphere_vm._parse_esx_memory_section(
        {
            "summary.quickStats.hostMemoryUsage": ["1"],
            "summary.quickStats.guestMemoryUsage": ["1"],
            "summary.quickStats.balloonedMemory": ["1"],
            "summary.quickStats.sharedMemory": ["1"],
            "summary.quickStats.privateMemory": ["1"],
        }
    )
    assert parsed_section == esx_vsphere.ESXMemory(
        host_usage=1048576.0,
        guest_usage=1048576.0,
        ballooned=1048576.0,
        private=1048576.0,
        shared=1048576.0,
    )


class ESXMemoryFactory(ModelFactory):
    __model__ = esx_vsphere.ESXMemory


def test_check_memory_usage():
    memory_section = esx_vsphere.ESXMemory(
        host_usage=1,
        guest_usage=1,
        ballooned=1,
        private=1,
        shared=1,
    )
    check_result = list(
        esx_vsphere_vm_mem_usage.check_mem_usage({}, _esx_vm_section(memory_section=memory_section))
    )
    results = [r for r in check_result if isinstance(r, Result)]
    assert [r.summary for r in results] == [
        "Host: 1 B",
        "Guest: 1 B",
        "Ballooned: 1 B",
        "Private: 1 B",
        "Shared: 1 B",
    ]


def test_check_memory_usage_metrics():
    memory_section = ESXMemoryFactory.build()
    check_result = list(
        esx_vsphere_vm_mem_usage.check_mem_usage({}, _esx_vm_section(memory_section))
    )
    metrics = [r for r in check_result if isinstance(r, Metric)]
    assert [m.name for m in metrics] == ["host", "guest", "ballooned", "private", "shared"]


def test_check_memory_usage_raises_error():
    with pytest.raises(IgnoreResultsError):
        list(esx_vsphere_vm_mem_usage.check_mem_usage({}, None))


def _esx_vm_section(memory_section: esx_vsphere.ESXMemory) -> esx_vsphere.ESXVm:
    return esx_vm_section(memory=memory_section, power_state="poweredOn")
