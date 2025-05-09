#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.vsphere.agent_based.esx_vsphere_counters import parse_esx_vsphere_counters
from cmk.plugins.vsphere.agent_based.esx_vsphere_datastore_io import (
    _check_esx_vsphere_datastore_io,
    discover_esx_vsphere_datastore_io,
)
from cmk.plugins.vsphere.lib.esx_vsphere import SectionCounter

STRING_TABLE = [  # only a snippet!
    ["datastore.datastoreReadIops", "56490e2e-692ac36c", "0#0", "number"],
    ["datastore.datastoreReadIops", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "0#0", "number"],
    ["datastore.datastoreReadIops", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "0#0", "number"],
    ["datastore.datastoreReadIops", "5847d774-2bdca236-23df-645106f0c5d0", "0#0", "number"],
    ["datastore.datastoreReadIops", "79d8b527-45291f84", "0#0", "number"],
    ["datastore.datastoreReadIops", "fce701f6-867094ae", "0#0", "number"],
    ["datastore.datastoreWriteIops", "56490e2e-692ac36c", "0#0", "number"],
    ["datastore.datastoreWriteIops", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "0#0", "number"],
    ["datastore.datastoreWriteIops", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "0#0", "number"],
    ["datastore.datastoreWriteIops", "5847d774-2bdca236-23df-645106f0c5d0", "0#0", "number"],
    ["datastore.datastoreWriteIops", "79d8b527-45291f84", "0#0", "number"],
    ["datastore.datastoreWriteIops", "fce701f6-867094ae", "0#0", "number"],
    ["datastore.name", "192.168.99.100:/vmtestnfs1", "NFS_sgrznac1_Test", "string"],
    ["datastore.name", "192.168.99.101:/vmprodnfs1", "NFS_sgrznac1_Prod", "string"],
    [
        "datastore.name",
        "192.168.99.99:/VeeamBackup_SGRZVeeam.acp.local",
        "VeeamBackup_SGRZVeeam.acp.local",
        "string",
    ],
    ["datastore.name", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "SSD_sgrz3par_vmstore1", "string"],
    ["datastore.name", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "vsa_vol1", "string"],
    ["datastore.name", "5847d774-2bdca236-23df-645106f0c5d0", "SSD_sgrz3par_vmstore2", "string"],
    ["datastore.name", "vvol:bf19e892e24d4f74-9246b507ebac9dec", "3par VVOL", "string"],
    ["datastore.read", "56490e2e-692ac36c", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "5847d774-2bdca236-23df-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "79d8b527-45291f84", "13#26", "kiloBytesPerSecond"],
    ["datastore.read", "fce701f6-867094ae", "0#0", "kiloBytesPerSecond"],
    ["datastore.sizeNormalizedDatastoreLatency", "56490e2e-692ac36c", "0#0", "microsecond"],
    [
        "datastore.sizeNormalizedDatastoreLatency",
        "576b8c5e-3d1e6844-ed6c-645106f0c5d0",
        "0#0",
        "microsecond",
    ],
    [
        "datastore.sizeNormalizedDatastoreLatency",
        "57e121ef-2bb2dbaa-ad99-645106f0c5d0",
        "0#0",
        "microsecond",
    ],
    [
        "datastore.sizeNormalizedDatastoreLatency",
        "5847d774-2bdca236-23df-645106f0c5d0",
        "0#0",
        "microsecond",
    ],
    ["datastore.sizeNormalizedDatastoreLatency", "79d8b527-45291f84", "0#0", "microsecond"],
    ["datastore.sizeNormalizedDatastoreLatency", "fce701f6-867094ae", "0#0", "microsecond"],
    ["datastore.write", "56490e2e-692ac36c", "0#0", "kiloBytesPerSecond"],
    ["datastore.write", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "0#5", "kiloBytesPerSecond"],
    ["datastore.write", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.write", "5847d774-2bdca236-23df-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.write", "79d8b527-45291f84", "891#543", "kiloBytesPerSecond"],
    ["datastore.write", "fce701f6-867094ae", "0#0", "kiloBytesPerSecond"],
]

STRING_TABLE_WITH_NEGATIVE_VALUES = [  # only a snippet!
    ["datastore.name", "192.168.99.100:/vmtestnfs1", "NFS_sgrznac1_Test", "string"],
    ["datastore.name", "192.168.99.101:/vmprodnfs1", "NFS_sgrznac1_Prod", "string"],
    [
        "datastore.name",
        "192.168.99.99:/VeeamBackup_SGRZVeeam.acp.local",
        "VeeamBackup_SGRZVeeam.acp.local",
        "string",
    ],
    ["datastore.name", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "SSD_sgrz3par_vmstore1", "string"],
    ["datastore.name", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "vsa_vol1", "string"],
    ["datastore.name", "5847d774-2bdca236-23df-645106f0c5d0", "SSD_sgrz3par_vmstore2", "string"],
    ["datastore.name", "vvol:bf19e892e24d4f74-9246b507ebac9dec", "3par VVOL", "string"],
    ["datastore.read", "56490e2e-692ac36c", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "576b8c5e-3d1e6844-ed6c-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "57e121ef-2bb2dbaa-ad99-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "5847d774-2bdca236-23df-645106f0c5d0", "0#0", "kiloBytesPerSecond"],
    ["datastore.read", "79d8b527-45291f84", "13#26", "kiloBytesPerSecond"],
    ["datastore.read", "fce701f6-867094ae", "0#0", "kiloBytesPerSecond"],
    ["datastore.sizeNormalizedDatastoreLatency", "56490e2e-692ac36c", "0#0", "microsecond"],
    [
        "datastore.sizeNormalizedDatastoreLatency",
        "576b8c5e-3d1e6844-ed6c-645106f0c5d0",
        "-1#-1",
        "microsecond",
    ],
    [
        "datastore.sizeNormalizedDatastoreLatency",
        "57e121ef-2bb2dbaa-ad99-645106f0c5d0",
        "0#0",
        "microsecond",
    ],
    [
        "datastore.sizeNormalizedDatastoreLatency",
        "5847d774-2bdca236-23df-645106f0c5d0",
        "0#0",
        "microsecond",
    ],
    ["datastore.sizeNormalizedDatastoreLatency", "79d8b527-45291f84", "0#0", "microsecond"],
    ["datastore.sizeNormalizedDatastoreLatency", "fce701f6-867094ae", "0#0", "microsecond"],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> SectionCounter:
    return parse_esx_vsphere_counters(STRING_TABLE)


@pytest.fixture(name="section_with_negative_values", scope="module")
def _get_section_negative_values() -> SectionCounter:
    return parse_esx_vsphere_counters(STRING_TABLE_WITH_NEGATIVE_VALUES)


def test_discovery_summary(section: SectionCounter) -> None:
    assert sorted(
        discover_esx_vsphere_datastore_io(
            [{"summary": True, "lvm": False, "vxvm": False, "diskless": False}],
            section,
        )
    ) == sorted(
        [
            Service(item="SUMMARY"),
        ]
    )


def test_discovery_physical(section: SectionCounter) -> None:
    assert sorted(
        discover_esx_vsphere_datastore_io(
            [
                {
                    "summary": False,
                    "physical": {"service_name": "name"},
                    "lvm": False,
                    "vxvm": False,
                    "diskless": False,
                }
            ],
            section,
        )
    ) == sorted(
        [
            Service(item="56490e2e-692ac36c"),
            Service(item="79d8b527-45291f84"),
            Service(item="SSD_sgrz3par_vmstore1"),
            Service(item="SSD_sgrz3par_vmstore2"),
            Service(item="fce701f6-867094ae"),
            Service(item="vsa_vol1"),
        ]
    )


def test_check_summary(section: SectionCounter) -> None:
    assert list(
        _check_esx_vsphere_datastore_io(
            "SUMMARY",
            {"summary": False, "physical": {}, "lvm": False, "vxvm": False, "diskless": False},
            section,
            1659382581,
            {},
        )
    ) == [
        Result(state=State.OK, summary="Read: 19.5 kB/s"),
        Metric("disk_read_throughput", 19456.0),
        Result(state=State.OK, summary="Write: 736 kB/s"),
        Metric("disk_write_throughput", 736256.0),
        Result(state=State.OK, notice="Read operations: 0.00/s"),
        Metric("disk_read_ios", 0.0),
        Result(state=State.OK, notice="Write operations: 0.00/s"),
        Metric("disk_write_ios", 0.0),
        Result(state=State.OK, summary="Latency: 0 seconds"),
        Metric("disk_latency", 0.0),
    ]


def test_check_summary_negative_values(section_with_negative_values: SectionCounter) -> None:
    assert list(
        _check_esx_vsphere_datastore_io("SUMMARY", {}, section_with_negative_values, 1659382581, {})
    ) == [
        Result(state=State.OK, summary="Read: 19.5 kB/s"),
        Metric("disk_read_throughput", 19456.0),
        Result(state=State.OK, summary="Latency: 0 seconds"),
        Metric("disk_latency", 0.0),
    ]


def test_check_item(section: SectionCounter) -> None:
    assert list(
        _check_esx_vsphere_datastore_io(
            "SSD_sgrz3par_vmstore1",
            {"summary": False, "physical": {}, "lvm": False, "vxvm": False, "diskless": False},
            section,
            1659382581,
            {},
        )
    ) == [
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
        Result(state=State.OK, summary="Write: 2.05 kB/s"),
        Metric("disk_write_throughput", 2048.0),
        Result(state=State.OK, notice="Read operations: 0.00/s"),
        Metric("disk_read_ios", 0.0),
        Result(state=State.OK, notice="Write operations: 0.00/s"),
        Metric("disk_write_ios", 0.0),
        Result(state=State.OK, summary="Latency: 0 seconds"),
        Metric("disk_latency", 0.0),
    ]


def test_check_item_negative_values(section_with_negative_values: SectionCounter) -> None:
    assert list(
        _check_esx_vsphere_datastore_io(
            "SSD_sgrz3par_vmstore1", {}, section_with_negative_values, 1659382581, {}
        )
    ) == [
        Result(state=State.OK, summary="Read: 0.00 B/s"),
        Metric("disk_read_throughput", 0.0),
    ]
