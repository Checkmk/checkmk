#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import TableRow
from cmk.plugins.vsphere.agent_based.inventory_esx_vsphere_clusters import (
    inventorize_esx_vsphere_clusters,
    parse_esx_vsphere_clusters,
)

STRING_TABLE = [
    ["datacenter-41", "hostsystems", "Cluster-A", "esx01", "esx02"],
    ["datacenter-41", "vms", "Cluster-A", "web-01", "db-01"],
    ["datacenter-41", "hostsystems", "Cluster-B", "esx03"],
    ["datacenter-41", "vms", "Cluster-B"],
]


def test_cluster_members_are_collected_per_cluster() -> None:
    section = parse_esx_vsphere_clusters(STRING_TABLE)

    assert section == {
        "Cluster-A": {
            "datacenter": "datacenter-41",
            "hostsystems": "esx01, esx02",
            "vms": "web-01, db-01",
        },
        "Cluster-B": {"datacenter": "datacenter-41", "hostsystems": "esx03", "vms": ""},
    }


def test_each_cluster_becomes_one_inventory_row() -> None:
    rows = list(inventorize_esx_vsphere_clusters(parse_esx_vsphere_clusters(STRING_TABLE)))

    assert [row.key_columns for row in rows if isinstance(row, TableRow)] == [
        {
            "cluster": "Cluster-A",
            "datacenter": "datacenter-41",
            "hostsystems": "esx01, esx02",
            "vms": "web-01, db-01",
        },
        {"cluster": "Cluster-B", "datacenter": "datacenter-41", "hostsystems": "esx03", "vms": ""},
    ]
    assert [row.path for row in rows if isinstance(row, TableRow)] == [
        ["software", "applications", "vmwareesx"],
        ["software", "applications", "vmwareesx"],
    ]
