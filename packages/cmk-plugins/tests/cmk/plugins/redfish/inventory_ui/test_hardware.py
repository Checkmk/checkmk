#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import Table
from cmk.plugins.redfish.inventory_ui.hardware import node_hardware_storage_redfish_drives


def test_node_has_expected_path() -> None:
    assert node_hardware_storage_redfish_drives.path == [
        "hardware",
        "storage",
        "redfish_drives",
    ]


def test_node_has_table_columns() -> None:
    assert isinstance(node_hardware_storage_redfish_drives.table, Table)
    columns = set(node_hardware_storage_redfish_drives.table.columns)
    assert columns == {
        "component",
        "manufacturer",
        "model",
        "serial",
        "firmware_version",
        "capacity_bytes",
        "media_type",
    }
