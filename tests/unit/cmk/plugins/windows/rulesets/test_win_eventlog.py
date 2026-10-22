#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.windows.rulesets.win_eventlog import migrate

_FILLED_EMPTY = {
    "filter_ids": [],
    "filter_sources": [],
    "filter_users": [],
    "text_pattern": [],
    "cluster_mapping": [],
    "vista_api": False,
}

_MIGRATED_FULL = {
    "event_logs": [
        {"log": ("named", "Application"), "severity": "warn", "context": True},
        {"log": ("all", None), "severity": "off", "context": False},
    ],
    "filter_ids": [{"log": ("all", None), "include": ["100", "200-300"], "exclude": []}],
    "filter_sources": [{"log": ("named", "System"), "include": [], "exclude": ["src"]}],
    "filter_users": [{"log": ("all", None), "include": ["admin"], "exclude": []}],
    "text_pattern": [{"log": ("named", "Security"), "pattern": ".*error.*"}],
    "sendall": True,
    "skip_duplicated": True,
    "cluster_mapping": [{"name": "cluster1", "ips": ["10.0.0.1"]}],
    "vista_api": True,
}


@pytest.mark.parametrize(
    "old, expected",
    [
        pytest.param(
            {"logfiles": [], "sendall": False, "skip_duplicated": False},
            {"event_logs": [], "sendall": False, "skip_duplicated": False, **_FILLED_EMPTY},
            id="old_minimal_is_filled",
        ),
        pytest.param(
            {
                "logfiles": [("Application", "warn", True), ("*", "off", False)],
                "filter_ids": [("*", ["100", "200-300"], [])],
                "filter_sources": [("System", [], ["src"])],
                "filter_users": [("*", ["admin"], [])],
                "text_pattern": [("Security", ".*error.*")],
                "sendall": True,
                "skip_duplicated": True,
                "cluster_mapping": [{"name": "cluster1", "ips": ["10.0.0.1"]}],
                "vista_api": True,
            },
            _MIGRATED_FULL,
            id="old_full",
        ),
        pytest.param(
            {
                "logfiles": [],
                "filter_ids": [("*", "", "")],
                "sendall": False,
                "skip_duplicated": False,
            },
            {
                "event_logs": [],
                "sendall": False,
                "skip_duplicated": False,
                **_FILLED_EMPTY,
                "filter_ids": [{"log": ("all", None), "include": [], "exclude": []}],
            },
            id="old_empty_string_means_all",
        ),
        pytest.param(_MIGRATED_FULL, _MIGRATED_FULL, id="already_migrated"),
        pytest.param({}, {}, id="new_empty"),
    ],
)
def test_migrate(old: object, expected: dict[str, object]) -> None:
    assert migrate(old) == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("x", id="str"),
        pytest.param(None, id="none"),
        pytest.param({"logfiles": [("Application", "warn")]}, id="malformed_event_log"),
        pytest.param({"logfiles": [], "filter_ids": [("*", None, [])]}, id="malformed_filter"),
    ],
)
def test_migrate_rejects_unknown_values(value: object) -> None:
    with pytest.raises(ValueError):
        migrate(value)
