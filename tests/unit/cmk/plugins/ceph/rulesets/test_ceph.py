#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.ceph.rulesets.ceph import migrate_bakery_rule


def _assert_migrates_to(value: object, expected: dict[str, object]) -> None:
    migrated = migrate_bakery_rule(value)
    assert migrated == expected
    assert migrate_bakery_rule(migrated) == expected


def test_migrate_bakery_rule_old_deploy() -> None:
    _assert_migrates_to(True, {"deploy": True, "interval": ("cached", 58.0)})


def test_migrate_bakery_rule_old_not_deploy() -> None:
    _assert_migrates_to(False, {"deploy": False, "interval": ("cached", 58.0)})


def test_migrate_bakery_rule_recent_not_deploy() -> None:
    _assert_migrates_to(None, {"deploy": False, "interval": ("cached", 58.0)})


def test_migrate_bakery_rule_recent_deploy() -> None:
    _assert_migrates_to({}, {"deploy": True})


def test_migrate_bakery_rule_recent_deploy_async() -> None:
    _assert_migrates_to({"interval": 123}, {"deploy": True, "interval": ("cached", 123.0)})


def test_migrate_bakery_rule_recent_deploy_client() -> None:
    _assert_migrates_to({"client": "Leo"}, {"deploy": True, "client": "Leo"})
