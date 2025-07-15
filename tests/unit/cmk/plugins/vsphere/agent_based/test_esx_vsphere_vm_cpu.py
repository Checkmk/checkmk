#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from polyfactory.factories.pydantic_factory import ModelFactory

from tests.unit.cmk.plugins.vsphere.agent_based.esx_vsphere_vm_util import esx_vm_section

from cmk.agent_based.v2 import Metric, Result
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_cpu
from cmk.plugins.vsphere.lib import esx_vsphere


class ESXCpuFactory(ModelFactory):
    __model__ = esx_vsphere.ESXCpu


def test_parse_esx_vsphere_cpu():
    parsed_section = esx_vsphere_vm._parse_esx_cpu_section(
        {
            "summary.quickStats.overallCpuUsage": ["1000"],
            "config.hardware.numCPU": ["1"],
            "config.hardware.numCoresPerSocket": ["2"],
        }
    )
    assert parsed_section == esx_vsphere.ESXCpu(
        overall_usage=1000, cpus_count=1, cores_per_socket=2
    )


def test_check_cpu():
    cpu_section = ESXCpuFactory.build(overall_usage=1000, cpus_count=1)
    check_result = list(esx_vsphere_vm_cpu.check_cpu(_esx_vm_section(cpu_section)))
    results = [r for r in check_result if isinstance(r, Result)]
    assert [r.summary for r in results] == ["demand is 1.000 Ghz, 1 virtual CPUs"]


def test_check_cpu_usage_metrics():
    cpu_section = ESXCpuFactory.build()
    check_result = list(esx_vsphere_vm_cpu.check_cpu(_esx_vm_section(cpu_section)))
    metrics = [r for r in check_result if isinstance(r, Metric)]
    assert [m.name for m in metrics] == ["demand"]


def _esx_vm_section(cpu: esx_vsphere.ESXCpu) -> esx_vsphere.SectionESXVm:
    return esx_vm_section(cpu=cpu)
