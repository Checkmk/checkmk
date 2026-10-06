#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Lives outside `cmk.gui.oauth` so the module-layer check keeps the oauth runtime from importing its own revisions."""

from cmk.schema_manager import ManagedDatabase, RevisionChain
from cmk.schema_manager.backend.sqlite import Sqlite
from cmk.schema_migrations.oauth._0001_initial_schema import InitialSchema

schema_manager_oauth = ManagedDatabase(
    name="oauth",
    backend=Sqlite(),
    chain=RevisionChain((InitialSchema(),)),
    omd_lifecycle=["create", "update"],
)
