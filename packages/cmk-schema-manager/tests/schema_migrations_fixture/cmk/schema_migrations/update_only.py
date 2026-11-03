#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from sqlite3 import Connection
from typing import override

from cmk.schema_manager.backend.sqlite import Sqlite
from cmk.schema_manager.managed_database import ManagedDatabase
from cmk.schema_manager.revision import Revision, RevisionChain


class InitialSchema(Revision[Connection]):
    id = "0001"

    @override
    def upgrade(self, context: Connection) -> None:
        pass


schema_manager_update_only = ManagedDatabase(
    name="update_only",
    backend=Sqlite(),
    chain=RevisionChain((InitialSchema(),)),
    omd_lifecycle=["update"],
)
