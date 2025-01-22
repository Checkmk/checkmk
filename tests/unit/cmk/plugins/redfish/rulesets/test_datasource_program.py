#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.redfish.rulesets.datasource_program import (
    migrate_redfish,
)


@pytest.mark.parametrize(
    "old, new",
    [
        pytest.param(
            {
                "user": "my-user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid5630c9e4-dfba-48a2-8b4f-f2c23bd457c4", "atshsth"),
                ),
            },
            {
                "user": "my-user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid5630c9e4-dfba-48a2-8b4f-f2c23bd457c4", "atshsth"),
                ),
                "port": 443,
                "proto": "https",
                "timeout": 3,
                "retries": 2,
                "debug": False,
            },
            id="minimal",
        ),
        pytest.param(
            {
                "user": "my-user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid5630c9e4-dfba-48a2-8b4f-f2c23bd457c4", "atshsth"),
                ),
                "disabled_sections": ["FirmwareInventory", "NetworkAdapters", "NetworkInterfaces"],
                "cached_sections": {"cache_time_Drives": 42},
                "proto": ("http", None),
                "timeout": 10,
            },
            {
                "user": "my-user",
                "password": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid5630c9e4-dfba-48a2-8b4f-f2c23bd457c4", "atshsth"),
                ),
                "fetching": {
                    "ArrayControllers": ("always", 0.0),
                    "Drives": ("cached", 42.0),
                    "EthernetInterfaces": ("always", 0.0),
                    "FirmwareInventory": ("never", -1.0),
                    "HostBusAdapters": ("always", 0.0),
                    "LogicalDrives": ("always", 0.0),
                    "Memory": ("always", 0.0),
                    "NetworkAdapters": ("never", -1.0),
                    "NetworkInterfaces": ("never", -1.0),
                    "PhysicalDrives": ("always", 0.0),
                    "Power": ("always", 0.0),
                    "Processors": ("always", 0.0),
                    "SimpleStorage": ("always", 0.0),
                    "SmartStorage": ("always", 0.0),
                    "Storage": ("always", 0.0),
                    "Thermal": ("always", 0.0),
                    "Volumes": ("always", 0.0),
                },
                "port": 443,
                "proto": "http",
                "timeout": 10.0,
                "retries": 2,
                "debug": False,
            },
            id="disabled and cached sections",
        ),
    ],
)
def test_migrate_redfish(old: object, new: Mapping[str, object]) -> None:
    assert migrate_redfish(old) == new
    assert migrate_redfish(new) == new
