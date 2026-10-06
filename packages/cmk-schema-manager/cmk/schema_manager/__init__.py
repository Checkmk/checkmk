#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.schema_manager._discovery import discover_db_migrations
from cmk.schema_manager._mechanism import ensure_schema
from cmk.schema_manager.errors import BackendUnavailableError
from cmk.schema_manager.managed_database import ManagedDatabase
from cmk.schema_manager.revision import Revision, RevisionChain

__all__ = [
    "BackendUnavailableError",
    "discover_db_migrations",
    "ensure_schema",
    "ManagedDatabase",
    "Revision",
    "RevisionChain",
]
