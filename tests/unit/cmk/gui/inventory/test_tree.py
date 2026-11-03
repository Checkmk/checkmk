#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest

import cmk.ccc.store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.gui.inventory import (
    get_history,
    load_delta_tree,
    load_latest_delta_tree,
    load_tree,
)
from cmk.inventory.history import HistoryStore
from cmk.inventory.trees import ImmutableTree


@pytest.mark.usefixtures("request_context")
def test_load_tree_of_a_row_without_a_host_is_empty() -> None:
    assert load_tree(host_name=HostName(""), raw_status_data_tree=b"") == ImmutableTree()


@pytest.mark.usefixtures("request_context")
def test_get_history_empty(tmp_path: Path) -> None:
    history, corrupted_history_files = get_history(
        HistoryStore(tmp_path),
        HostName("inv-host"),
    )
    assert len(history) == 0
    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("request_context")
def test_get_history_archive_but_no_inv_tree(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )

    history, corrupted_history_files = get_history(history_store, hostname)

    assert len(history) == 1
    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("request_context")
def test_get_history(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        {"inv": "attr-1"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        {"inv-2": "attr"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        {"inv": "attr-3"},
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )
    os.utime(tmp_path / "var/check_mk/inventory" / hostname, (100, 100))

    expected_results = [
        (1, 0, 0),
        (0, 1, 0),
        (1, 0, 1),
        (1, 0, 1),
        (0, 1, 0),
    ]

    history, corrupted_history_files = get_history(history_store, hostname)

    assert len(history) == 5

    for entry, expected_result in zip(history, expected_results):
        e_new, e_changed, e_removed = expected_result
        assert isinstance(entry.current_timestamp, int)
        assert entry.new == e_new
        assert entry.changed == e_changed
        assert entry.removed == e_removed

    assert len(corrupted_history_files) == 0

    for delta_cache_filename, expected_delta_cache_filename in zip(
        sorted(
            [
                fp.name
                for fp in (tmp_path / "var/check_mk/inventory_delta_cache" / hostname).iterdir()
            ]
        ),
        sorted(
            [
                "0_1.json",
                "1_2.json",
                "2_3.json",
                "None_0.json",
            ]
        ),
    ):
        assert delta_cache_filename == expected_delta_cache_filename


@pytest.mark.usefixtures("request_context")
def test_get_history_corrupted_files(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")
    archive_dir = tmp_path / "var/check_mk/inventory_archive" / hostname
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "foo").touch()

    history, corrupted_history_files = get_history(history_store, hostname)
    assert not history
    assert corrupted_history_files == ["inventory_archive/inv-host/foo"]


@pytest.mark.parametrize("search_timestamp", [0, 1, 2, 3])
@pytest.mark.usefixtures("request_context")
def test_load_delta_tree(tmp_path: Path, search_timestamp: int) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        {"inv": "attr-1"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        {"inv-2": "attr"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        {"inv": "attr-3"},
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    _delta_tree, corrupted_history_files = load_delta_tree(
        history_store,
        hostname,
        search_timestamp,
    )

    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("request_context")
def test_load_delta_tree_no_such_timestamp(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        {"inv": "attr-1"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        {"inv-2": "attr"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        {"inv": "attr-3"},
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    with pytest.raises(MKGeneralException) as e:
        load_delta_tree(history_store, hostname, -1)
    assert str(e.value) == "Found no history entry at the time of '-1' for the host 'inv-host'"


@pytest.mark.usefixtures("request_context")
def test_load_latest_delta_tree(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        {"inv": "attr-1"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        {"inv-2": "attr"},
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        {"inv": "attr-3"},
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    search_timestamp = int((tmp_path / "var/check_mk/inventory" / hostname).stat().st_mtime)

    _delta_tree, corrupted_history_files = load_delta_tree(
        history_store, hostname, search_timestamp
    )

    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("request_context")
def test_load_latest_delta_tree_no_archive_and_inv_tree(tmp_path: Path) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    assert not load_latest_delta_tree(history_store, hostname)
