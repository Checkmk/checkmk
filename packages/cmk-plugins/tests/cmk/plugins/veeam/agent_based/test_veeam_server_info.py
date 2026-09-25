#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime

from cmk.agent_based.v2 import Attributes, TableRow
from cmk.plugins.veeam.agent_based.veeam_server_info import (
    inventory_veeam_server,
    parse_veeam_server_info,
)


def _server_info(**overrides: object) -> list[list[str]]:
    info: dict[str, object] = {
        "vbrId": "a8d6e3b1-3f0c-4a1e-9c5e-2b7f8d4c6a10",
        "name": "backup-server-01",
        "buildVersion": "12.3.1.1139",
        "platform": "Windows",
        "patches": ["KB4696", "KB4711"],
        "databaseVendor": "PostgreSql",
        "sqlServerEdition": "",
        "sqlServerVersion": "15.10",
        "databaseSchemaVersion": "12.3.1.1139",
        "databaseContentVersion": "2025-03-01",
        "veeamRegistration": {
            "isRegistered": True,
            "expirationDate": "2027-01-31T00:00:00+00:00",
        },
    }
    info.update(overrides)
    return [[json.dumps(info)]]


def _inventory(string_table: list[list[str]]) -> list[Attributes | TableRow]:
    assert (section := parse_veeam_server_info(string_table)) is not None
    return list(inventory_veeam_server(section))


def test_backup_server_is_inventorized_with_its_patches() -> None:
    assert _inventory(_server_info()) == [
        Attributes(
            path=["software", "applications", "veeam", "backup_server"],
            inventory_attributes={
                "name": "backup-server-01",
                "build_version": "12.3.1.1139",
                "platform": "Windows",
                "database_vendor": "PostgreSql",
                "sql_server_edition": "",
                "sql_server_version": "15.10",
                "vbr_id": "a8d6e3b1-3f0c-4a1e-9c5e-2b7f8d4c6a10",
                "database_schema_version": "12.3.1.1139",
                "database_content_version": "2025-03-01",
                "is_registered": True,
                "registration_expiration_date": datetime.fromisoformat(
                    "2027-01-31T00:00:00+00:00"
                ).timestamp(),
            },
        ),
        TableRow(
            path=["software", "applications", "veeam", "patches"], key_columns={"name": "KB4696"}
        ),
        TableRow(
            path=["software", "applications", "veeam", "patches"], key_columns={"name": "KB4711"}
        ),
    ]


def test_registration_without_expiration_date_is_inventorized_without_it() -> None:
    string_table = _server_info(veeamRegistration={"isRegistered": False})

    attributes = _inventory(string_table)[0]

    assert isinstance(attributes, Attributes)
    assert attributes.inventory_attributes["is_registered"] is False
    assert "registration_expiration_date" not in attributes.inventory_attributes


def test_server_without_patches_has_no_patch_rows() -> None:
    assert _inventory(_server_info(patches=[]))[1:] == []


def test_empty_section_is_not_parsed() -> None:
    assert parse_veeam_server_info([]) is None
