#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.broadcom_storage.rulesets.storcli import migrate


def test_migrate_none_gives_do_not_deploy() -> None:
    assert migrate(None) == {"deployment": ("do_not_deploy", None)}


def test_migrate_string_gives_sync_with_path() -> None:
    path = r"C:\Program Files\StorCLI\storcli64.exe"
    assert migrate(path) == {"deployment": ("sync", None), "storcli_path": path}


def test_migrate_already_migrated_sync_passthrough() -> None:
    migrated = {"deployment": ("sync", None), "storcli_path": r"C:\storcli64.exe"}
    assert migrate(migrated) == migrated


def test_migrate_already_migrated_do_not_deploy_passthrough() -> None:
    migrated = {"deployment": ("do_not_deploy", None)}
    assert migrate(migrated) == migrated


def test_migrate_already_migrated_cached_passthrough() -> None:
    migrated = {"deployment": ("cached", 3600.0)}
    assert migrate(migrated) == migrated


def test_migrate_unexpected_type_raises() -> None:
    with pytest.raises(ValueError, match="Unexpected value"):
        migrate(42)
