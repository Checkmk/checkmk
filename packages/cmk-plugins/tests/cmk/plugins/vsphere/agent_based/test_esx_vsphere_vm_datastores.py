#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"


from cmk.agent_based.v2 import Result
from cmk.plugins.vsphere.agent_based import esx_vsphere_vm, esx_vsphere_vm_datastores
from cmk.plugins.vsphere.lib import esx_vsphere


def test_parse_esx_vsphere_datastore() -> None:
    parsed_section = esx_vsphere_vm.parse_esx_datastore_section(
        {
            "config.datastoreUrl": [
                "maintenanceMode",
                "normal|url",
                "ds:///vmfs/volumes/vsan:5239d5cbf4c95b8c-5977b0e019a35313/|uncommitted",
                "1|name",
                "vsanDatastore|type",
                "vsan|accessible",
                "true|capacity",
                "1|freeSpace",
                "1",
            ]
        }
    )
    assert parsed_section == [
        esx_vsphere.ESXDataStore(
            name="vsanDatastore",
            free_space=1.0,
            capacity=1.0,
        )
    ]


def test_check_datastore() -> None:
    section = esx_vsphere.SectionESXVm(
        mounted_devices=(),
        snapshots=(),
        status=None,
        power_state=None,
        memory=None,
        cpu=None,
        datastores=[
            esx_vsphere.ESXDataStore(
                name="datastore1",
                free_space=20938787651584.0,
                capacity=31686121226240.0,
            )
        ],
        heartbeat=None,
        host=None,
        name=None,
        systime=None,
    )
    check_result = list(esx_vsphere_vm_datastores.check_datastores(section))
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].summary.endswith("(28.8 TiB/66.1% free)")


def test_check_datastore_with_no_capacity() -> None:
    section = esx_vsphere.SectionESXVm(
        mounted_devices=(),
        snapshots=(),
        status=None,
        power_state=None,
        memory=None,
        cpu=None,
        datastores=[
            esx_vsphere.ESXDataStore(
                name="datastore1",
                free_space=20938787651584.0,
                capacity=0.0,
            )
        ],
        heartbeat=None,
        host=None,
        name=None,
        systime=None,
    )
    check_result = list(esx_vsphere_vm_datastores.check_datastores(section))
    results = [r for r in check_result if isinstance(r, Result)]
    assert len(results) == 1
    assert results[0].summary.endswith("(0 B/0.0% free)")
