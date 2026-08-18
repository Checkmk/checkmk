#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.gui.search import index


@pytest.fixture(autouse=True)
def update_requests_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(index, "_PATH_UPDATE_REQUESTS", tmp_path / "search_index_updates.json")


def test_updates_requested_false_when_no_file_exists() -> None:
    assert index._updates_requested() is False


def test_updates_requested_true_after_rebuild_request() -> None:
    index.request_rebuild()
    assert index._updates_requested() is True


def test_updates_requested_true_after_update_request() -> None:
    index.request_update("some_change")
    assert index._updates_requested() is True


def test_request_index_rebuild_sets_rebuild_flag() -> None:
    index.request_rebuild()

    value = index._read_and_remove_update_requests()
    expected = {"rebuild": True, "change_actions": []}

    assert value == expected


def test_request_index_update_appends_change_action() -> None:
    index.request_update("foo")
    index.request_update("bar")

    value = index._read_and_remove_update_requests()
    expected = {"rebuild": False, "change_actions": ["foo", "bar"]}

    assert value == expected


def test_request_index_rebuild_preserves_existing_change_actions() -> None:
    index.request_update("foo")
    index.request_rebuild()

    value = index._read_and_remove_update_requests()
    expected = {"rebuild": True, "change_actions": ["foo"]}

    assert value == expected


def test_read_and_remove_update_requests_removes_file() -> None:
    index.request_rebuild()
    index._read_and_remove_update_requests()
    assert index._updates_requested() is False


def test_read_and_remove_update_requests_defaults_when_no_file_exists() -> None:
    assert index._read_and_remove_update_requests() == {"rebuild": False, "change_actions": []}


def test_read_and_remove_update_requests_defaults_on_corrupted_json() -> None:
    index._PATH_UPDATE_REQUESTS.write_text("not valid json")

    value = index._read_and_remove_update_requests()
    expected = {"rebuild": False, "change_actions": []}

    assert value == expected


def test_read_and_remove_update_requests_defaults_on_missing_keys() -> None:
    index._PATH_UPDATE_REQUESTS.write_text('{"rebuild": true}')

    value = index._read_and_remove_update_requests()
    expected = {"rebuild": False, "change_actions": []}

    assert value == expected


def test_read_and_remove_update_requests_coerces_change_action_types() -> None:
    index._PATH_UPDATE_REQUESTS.write_text('{"rebuild": false, "change_actions": [1, 2]}')

    value = index._read_and_remove_update_requests()
    expected = {"rebuild": False, "change_actions": ["1", "2"]}

    assert value == expected


def test_main_requests_an_index_rebuild() -> None:
    index.main()

    assert index._read_and_remove_update_requests() == {"rebuild": True, "change_actions": []}


def test_main_reports_a_failed_request_without_raising(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # main() is the init-redis entry point, so a site must still come up when the
    # rebuild request cannot be written.
    def _fail() -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr(index, "request_rebuild", _fail)

    index.main()

    assert "Failed to request building of Setup search index" in caplog.text
    assert index._updates_requested() is False
