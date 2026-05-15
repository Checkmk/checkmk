#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_cpu
from cmk.plugins.vsphere.lib import esx_vsphere

_SECTION_NO_CPU = esx_vsphere.SectionESXVm(
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


def test_parse_esx_vsphere_cpu() -> None:
    parsed_section = esx_vsphere_vm.parse_esx_cpu_section(
        {
            "summary.quickStats.overallCpuUsage": ["1000"],
            "config.hardware.numCPU": ["1"],
            "config.hardware.numCoresPerSocket": ["2"],
        }
    )
    assert parsed_section == esx_vsphere.ESXCpu(
        overall_usage=1000, cpus_count=1, cores_per_socket=2
    )


def test_check_cpu() -> None:
    section = esx_vsphere.SectionESXVm(
        mounted_devices=(),
        snapshots=(),
        status=None,
        power_state=None,
        memory=None,
        cpu=esx_vsphere.ESXCpu(
            overall_usage=1000,
            cpus_count=1,
            cores_per_socket=0,
        ),
        datastores=(),
        heartbeat=None,
        host=None,
        name=None,
        systime=None,
    )
    check_result = list(esx_vsphere_vm_cpu.check_cpu(section))
    results = [r for r in check_result if isinstance(r, Result)]
    assert [r.summary for r in results] == ["demand is 1.000 Ghz, 1 virtual CPUs"]


def test_check_cpu_usage_metrics() -> None:
    section = esx_vsphere.SectionESXVm(
        mounted_devices=(),
        snapshots=(),
        status=None,
        power_state=None,
        memory=None,
        cpu=esx_vsphere.ESXCpu(
            overall_usage=0,
            cpus_count=0,
            cores_per_socket=0,
        ),
        datastores=(),
        heartbeat=None,
        host=None,
        name=None,
        systime=None,
    )
    check_result = list(esx_vsphere_vm_cpu.check_cpu(section))
    metrics = [r for r in check_result if isinstance(r, Metric)]
    assert [m.name for m in metrics] == ["demand"]


def test_check_cpu_raises_when_cpu_missing() -> None:
    # Lock in the "VM powered off" branch: cpu=None must raise
    # IgnoreResultsError. The plugin has no configurable params, so the
    # only state-relevant branch is this control-flow guard.
    with pytest.raises(
        IgnoreResultsError,
        match=r"^No information about CPU usage\. VM is probably powered off\.$",
    ):
        list(esx_vsphere_vm_cpu.check_cpu(_SECTION_NO_CPU))
