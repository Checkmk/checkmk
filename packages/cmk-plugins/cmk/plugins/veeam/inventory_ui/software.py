#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.inventory_ui.v1 import BoolField, Label, Node, NumberField, Table, TextField, Title, View


def _render_date(value: int | float) -> Label | str:
    return time.strftime("%Y-%m-%d", time.localtime(value))


node_software_applications_veeam = Node(
    name="software_applications_veeam",
    path=["software", "applications", "veeam"],
    title=Title("Veeam Backup & Replication"),
)

node_software_applications_veeam_backup_server = Node(
    name="software_applications_veeam_backup_server",
    path=["software", "applications", "veeam", "backup_server"],
    title=Title("Backup server"),
    attributes={
        "name": TextField(Title("Name")),
        "build_version": TextField(Title("Build version")),
        "platform": TextField(Title("Platform")),
        "database_vendor": TextField(Title("Database vendor")),
        "sql_server_edition": TextField(Title("SQL Server edition")),
        "sql_server_version": TextField(Title("SQL Server version")),
        "vbr_id": TextField(Title("Installation ID")),
        "database_schema_version": TextField(Title("Database schema version")),
        "database_content_version": TextField(Title("Database content version")),
        "is_registered": BoolField(Title("Registered with Veeam")),
        "registration_expiration_date": NumberField(
            Title("Registration expiration date"), render=_render_date
        ),
    },
)

node_software_applications_veeam_patches = Node(
    name="software_applications_veeam_patches",
    path=["software", "applications", "veeam", "patches"],
    title=Title("Patches"),
    table=Table(
        view=View(name="invveeampatches", title=Title("Veeam Backup & Replication patches")),
        columns={
            "name": TextField(Title("Name")),
        },
    ),
)
