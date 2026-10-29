#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A type parameter's bound cannot refer to another one, so any backend is Backend[Any].
# mypy: disable-error-code="explicit-any"
"""Discovery of `ManagedDatabase` registrations via the `cmk.schema_migrations` namespace."""

from collections.abc import Mapping
from typing import Any, cast

from cmk.discover_plugins import (
    discover_plugins_from_modules,
    discover_submodules,
    PluginLocation,
)
from cmk.schema_manager.backend.base import Backend
from cmk.schema_manager.managed_database import ManagedDatabase, OmdLifecycleEvent

SCHEMA_MIGRATIONS_NAMESPACE = "cmk.schema_migrations"


def discover_db_migrations[BackendT: Backend[Any]](
    *, backend_type: type[BackendT], event: OmdLifecycleEvent | None = None
) -> Mapping[PluginLocation, ManagedDatabase[Any, BackendT]]:
    """The registered databases whose backend is a `backend_type`."""
    found = discover_plugins_from_modules(
        {ManagedDatabase: "schema_manager_"},
        discover_submodules(SCHEMA_MIGRATIONS_NAMESPACE, raise_errors=True),
        skip_wrong_types=False,
        raise_errors=True,
    ).plugins
    return {
        # mypy cannot narrow BackendT from isinstance on the backend.
        location: cast(ManagedDatabase[Any, BackendT], database)
        for location, database in found.items()
        if isinstance(database.backend, backend_type)
        and (event is None or event in database.omd_lifecycle)
    }
