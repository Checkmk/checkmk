#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.collection.rulesets.arcserve_backup import migrate


def test_migrate_none_gives_do_not_deploy() -> None:
    assert migrate(None) == {"deployment": ("do_not_deploy", None)}


def test_migrate_old_dict_with_sqlserver_gives_sync() -> None:
    assert migrate({"sqlserver": r"SATURN\ARCSERVE_DB"}) == {
        "deployment": ("sync", None),
        "sqlserver": r"SATURN\ARCSERVE_DB",
    }


def test_migrate_old_dict_without_sqlserver_gives_sync() -> None:
    assert migrate({}) == {"deployment": ("sync", None)}


def test_migrate_already_migrated_passthrough() -> None:
    migrated = {"deployment": ("sync", None), "sqlserver": "server"}
    assert migrate(migrated) == migrated


def test_migrate_already_migrated_do_not_deploy_passthrough() -> None:
    migrated = {"deployment": ("do_not_deploy", None)}
    assert migrate(migrated) == migrated


def test_migrate_unexpected_type_raises() -> None:
    with pytest.raises(ValueError, match="Unexpected value"):
        migrate("unexpected_string")
