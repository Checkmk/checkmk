#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.inotify.rulesets.bakery import migrate

_MIGRATED = {
    "deployment": ("sync", None),
    "heartbeat_timeout": 120.0,
    "write_interval": 10.0,
    "max_messages_per_interval": 100,
    "stats_retention": 120.0,
    "entries": [
        ("folder", {"path": "/var/log", "operations": ["create", "delete"]}),
        ("files", {"path": "/etc", "files": ["passwd", "shadow"], "operations": ["modify"]}),
    ],
}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(None, {"deployment": ("do_not_deploy", None)}, id="do_not_deploy"),
        pytest.param(
            (
                120,
                10,
                100,
                120,
                [
                    ("/var/log", ["create", "delete"]),
                    ("/etc", ["passwd", "shadow"], ["modify"]),
                ],
            ),
            _MIGRATED,
            id="old_tuple",
        ),
        pytest.param(_MIGRATED, _MIGRATED, id="already_migrated"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


def test_migrate_converts_times_to_float() -> None:
    migrated = migrate((120, 10, 100, 120, []))
    assert all(
        isinstance(migrated[key], float)
        for key in ("heartbeat_timeout", "write_interval", "stats_retention")
    )
    assert isinstance(migrated["max_messages_per_interval"], int)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("unexpected", id="str"),
        pytest.param({}, id="empty_dict"),
        pytest.param((120, 10, 100, 120), id="tuple_without_entries"),
        pytest.param((120, 10, 100, 120, [("/etc", "passwd", ["modify"])]), id="malformed_entry"),
    ],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
