#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from cmk.bakery.v1 import WindowsConfigEntry
from cmk.base.plugins.bakery.win_eventlog import get_win_eventlog_windows_config


def test_win_eventlog_minimal_config() -> None:
    conf: dict[str, object] = {}
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
    ]


def test_win_eventlog_sendall_true() -> None:
    conf = {"sendall": True}
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=True),
    ]


def test_win_eventlog_vista_api() -> None:
    conf = {"vista_api": True}
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(path=["logwatch", "vista_api"], content=True),
    ]


def test_win_eventlog_skip_duplicated() -> None:
    conf = {"skip_duplicated": True}
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(path=["logwatch", "skip_duplicated"], content=True),
    ]


def test_win_eventlog_logfiles() -> None:
    conf = {
        "logfiles": [
            ("Application", "warn", True),
            ("System", "crit", False),
        ],
    }
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "logfile"],
            content=[
                {"application": "warn context"},
                {"system": "crit nocontext"},
            ],
        ),
    ]


def test_win_eventlog_filter_ids() -> None:
    conf = {
        "filter_ids": [
            ("Application", ["100", "200"], ["300"]),
        ],
    }
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "filter_ids"],
            content=[{"application": "100;200;;300"}],
        ),
    ]


def test_win_eventlog_filter_sources() -> None:
    conf = {
        "filter_sources": [
            ("System", ["src1"], ["src2", "src3"]),
        ],
    }
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "filter_sources"],
            content=[{"system": "src1;;src2;src3"}],
        ),
    ]


def test_win_eventlog_filter_users() -> None:
    conf: dict[str, Any] = {
        "filter_users": [
            ("Security", ["admin"], []),
        ],
    }
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "filter_users"],
            content=[{"security": "admin;;"}],
        ),
    ]


def test_win_eventlog_cluster_mapping() -> None:
    conf = {
        "cluster_mapping": [
            {"name": "cluster1", "ips": ["10.0.0.1", "10.0.0.2"]},
        ],
    }
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "clusters"],
            content={"cluster1": ["10.0.0.1", "10.0.0.2"]},
        ),
    ]


def test_win_eventlog_text_pattern() -> None:
    conf = {
        "text_pattern": [
            ("OK", ".*success.*"),
            ("CRIT", ".*error.*"),
        ],
    }
    result = list(get_win_eventlog_windows_config(conf))
    assert result == [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "text_pattern"],
            content=["ok:.*success.*", "crit:.*error.*"],
        ),
    ]


def test_win_eventlog_full_config() -> None:
    conf = {
        "sendall": True,
        "vista_api": True,
        "skip_duplicated": False,
        "logfiles": [("Application", "warn", True)],
        "filter_ids": [("Application", ["100"], ["200"])],
        "filter_sources": [("System", ["src1"], [])],
        "filter_users": [("Security", [], ["guest"])],
        "cluster_mapping": [{"name": "mycluster", "ips": ["1.2.3.4"]}],
        "text_pattern": [("WARN", ".*warning.*")],
    }
    result = list(get_win_eventlog_windows_config(conf))
    expected = [
        WindowsConfigEntry(path=["logwatch", "sendall"], content=True),
        WindowsConfigEntry(path=["logwatch", "vista_api"], content=True),
        WindowsConfigEntry(path=["logwatch", "skip_duplicated"], content=False),
        WindowsConfigEntry(
            path=["logwatch", "logfile"],
            content=[{"application": "warn context"}],
        ),
        WindowsConfigEntry(
            path=["logwatch", "filter_ids"],
            content=[{"application": "100;;200"}],
        ),
        WindowsConfigEntry(
            path=["logwatch", "filter_sources"],
            content=[{"system": "src1;;"}],
        ),
        WindowsConfigEntry(
            path=["logwatch", "filter_users"],
            content=[{"security": ";;guest"}],
        ),
        WindowsConfigEntry(
            path=["logwatch", "clusters"],
            content={"mycluster": ["1.2.3.4"]},
        ),
        WindowsConfigEntry(
            path=["logwatch", "text_pattern"],
            content=["warn:.*warning.*"],
        ),
    ]
    assert result == expected
