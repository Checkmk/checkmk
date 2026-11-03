#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.esx_vsphere_datastores import (
    check_esx_vsphere_datastores,
    discover_esx_vsphere_datastores,
    parse_esx_vsphere_datastores,
)

from cmk.agent_based.v2 import StringTable

_STRING_TABLE_SHARED_NAME: StringTable = [
    ["[datastore1]"],
    ["accessible", "true"],
    ["capacity", "107374182400"],
    ["freeSpace", "80530636800"],
    ["url", "ds:///vmfs/volumes/563b3611-f9333855-cfa1-00215e221152/"],
    ["[san-ds01]"],
    ["accessible", "true"],
    ["capacity", "1099511627776"],
    ["freeSpace", "549755813888"],
    ["url", "ds:///vmfs/volumes/04cc2737-7d460e93/"],
    ["[datastore1]"],
    ["accessible", "true"],
    ["capacity", "214748364800"],
    ["freeSpace", "53687091200"],
    ["url", "ds:///vmfs/volumes/vsan:5239d5cbf4c95b8c-5977b0e019a35313/"],
]


def test_only_datastores_sharing_a_name_get_their_volume_id_appended() -> None:
    section = parse_esx_vsphere_datastores(_STRING_TABLE_SHARED_NAME)

    services = list(discover_esx_vsphere_datastores(section))

    assert services == [
        ("datastore1 563b3611-f9333855-cfa1-00215e221152", {}),
        ("san-ds01", {}),
        ("datastore1 vsan:5239d5cbf4c95b8c-5977b0e019a35313", {}),
    ]


def test_datastores_sharing_a_name_keep_their_own_values() -> None:
    section = parse_esx_vsphere_datastores(_STRING_TABLE_SHARED_NAME)

    first_capacity = section["datastore1 563b3611-f9333855-cfa1-00215e221152"].get("capacity")
    second_capacity = section["datastore1 vsan:5239d5cbf4c95b8c-5977b0e019a35313"].get("capacity")

    assert first_capacity == 107374182400
    assert second_capacity == 214748364800


def test_name_shared_by_several_datastores_matches_none_of_them() -> None:
    section = parse_esx_vsphere_datastores(_STRING_TABLE_SHARED_NAME)

    results = list(check_esx_vsphere_datastores("datastore1", {}, section))

    assert not results
