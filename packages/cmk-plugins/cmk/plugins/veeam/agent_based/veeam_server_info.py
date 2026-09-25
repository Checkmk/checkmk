#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)
from cmk.plugins.veeam.lib import parse_iso8601_epoch


@dataclass(frozen=True, kw_only=True)
class BackupServer:
    """Mirrors the VBR REST API's ServerInfoModel (GET /api/v1/serverInfo, 1.3-rev0)."""

    name: str
    build_version: str
    platform: str
    database_vendor: str
    sql_server_edition: str
    sql_server_version: str
    vbr_id: str
    database_schema_version: str
    database_content_version: str
    is_registered: bool
    registration_expiration_date: float | None
    patches: Sequence[str]


def parse_veeam_server_info(string_table: StringTable) -> BackupServer | None:
    if not string_table:
        return None
    info = json.loads(string_table[0][0])
    registration = info["veeamRegistration"]
    expiration_date = registration.get("expirationDate")
    return BackupServer(
        name=info["name"],
        build_version=info["buildVersion"],
        platform=info["platform"],
        database_vendor=info["databaseVendor"],
        sql_server_edition=info["sqlServerEdition"],
        sql_server_version=info["sqlServerVersion"],
        vbr_id=info["vbrId"],
        database_schema_version=info["databaseSchemaVersion"],
        database_content_version=info["databaseContentVersion"],
        is_registered=registration["isRegistered"],
        registration_expiration_date=(
            None if expiration_date is None else parse_iso8601_epoch(expiration_date)
        ),
        patches=info["patches"],
    )


agent_section_veeam_server_info = AgentSection(
    name="veeam_server_info",
    parse_function=parse_veeam_server_info,
)


def inventory_veeam_server(section: BackupServer) -> InventoryResult:
    yield Attributes(
        path=["software", "applications", "veeam", "backup_server"],
        inventory_attributes={
            "name": section.name,
            "build_version": section.build_version,
            "platform": section.platform,
            "database_vendor": section.database_vendor,
            "sql_server_edition": section.sql_server_edition,
            "sql_server_version": section.sql_server_version,
            "vbr_id": section.vbr_id,
            "database_schema_version": section.database_schema_version,
            "database_content_version": section.database_content_version,
            "is_registered": section.is_registered,
            **(
                {}
                if section.registration_expiration_date is None
                else {"registration_expiration_date": section.registration_expiration_date}
            ),
        },
    )
    for patch in section.patches:
        yield TableRow(
            path=["software", "applications", "veeam", "patches"],
            key_columns={"name": patch},
        )


inventory_plugin_veeam_server = InventoryPlugin(
    name="veeam_server",
    sections=["veeam_server_info"],
    inventory_function=inventory_veeam_server,
)
