#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.discover_plugins import PluginLocation
from cmk.schema_manager._discovery import discover_db_migrations, SCHEMA_MIGRATIONS_NAMESPACE
from cmk.schema_manager.backend.sqlite import Sqlite

pytestmark = pytest.mark.usefixtures("registered_fixture_databases")


def _location(name: str) -> PluginLocation:
    return PluginLocation(f"{SCHEMA_MIGRATIONS_NAMESPACE}.{name}", f"schema_manager_{name}")


def test_discover_db_migrations_finds_every_registered_database() -> None:
    found = discover_db_migrations(backend_type=Sqlite)

    assert found[_location("create_and_update")].name == "create_and_update"
    assert found[_location("update_only")].name == "update_only"


def test_discover_db_migrations_keeps_only_databases_with_the_requested_event() -> None:
    assert list(discover_db_migrations(backend_type=Sqlite, event="create")) == [
        _location("create_and_update")
    ]


class _OtherSqlite(Sqlite):
    pass


def test_discover_db_migrations_filters_out_databases_of_another_backend_type() -> None:
    assert discover_db_migrations(backend_type=_OtherSqlite) == {}
