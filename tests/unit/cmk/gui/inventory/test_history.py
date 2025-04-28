#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.ccc.store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import deserialize_tree, HistoryStore, serialize_tree

from cmk.gui.inventory._history import get_history, load_delta_tree, load_latest_delta_tree


def test_get_history_empty(tmp_path: Path, request_context: None) -> None:
    history, corrupted_history_files = get_history(
        HistoryStore(tmp_path),
        HostName("inv-host"),
    )
    assert len(history) == 0
    assert len(corrupted_history_files) == 0


def test_get_history_archive_but_no_inv_tree(tmp_path: Path, request_context: None) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )

    history, corrupted_history_files = get_history(history_store, hostname)

    assert len(history) == 1
    assert len(corrupted_history_files) == 0


def test_get_history(tmp_path: Path, request_context: None) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        serialize_tree(deserialize_tree({"inv": "attr-1"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        serialize_tree(deserialize_tree({"inv-2": "attr"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        serialize_tree(deserialize_tree({"inv": "attr-3"})),
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

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
        assert isinstance(entry.timestamp, int)
        assert entry.new == e_new
        assert entry.changed == e_changed
        assert entry.removed == e_removed

    assert len(corrupted_history_files) == 0

    for delta_cache_filename, expected_delta_cache_filename in zip(
        sorted(
            [
                fp.name
                for fp in (tmp_path / "var/check_mk/inventory_delta_cache" / hostname).iterdir()
                # Timestamp of current inventory tree is not static
                if not fp.name.startswith("3_")
            ]
        ),
        sorted(
            [
                "0_1",
                "1_2",
                "2_3",
                "None_0",
            ]
        ),
    ):
        assert delta_cache_filename == expected_delta_cache_filename


def test_get_history_corrupted_files(tmp_path: Path, request_context: None) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")
    archive_dir = tmp_path / "var/check_mk/inventory_archive" / hostname
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "foo").touch()

    history, corrupted_history_files = get_history(history_store, hostname)
    assert not history
    assert corrupted_history_files == ["inventory_archive/inv-host/foo"]


@pytest.mark.parametrize(
    "search_timestamp, expected_raw_delta_tree",
    [
        (0, {"inv": (None, "attr-0")}),
        (1, {"inv": ("attr-0", "attr-1")}),
        (2, {"inv": ("attr-1", None), "inv-2": (None, "attr")}),
        (3, {"inv": (None, "attr-3"), "inv-2": ("attr", None)}),
    ],
)
def test_load_delta_tree(
    tmp_path: Path,
    search_timestamp: int,
    expected_raw_delta_tree: dict,
    request_context: None,
) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        serialize_tree(deserialize_tree({"inv": "attr-1"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        serialize_tree(deserialize_tree({"inv-2": "attr"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        serialize_tree(deserialize_tree({"inv": "attr-3"})),
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    delta_tree, corrupted_history_files = load_delta_tree(
        history_store,
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0


def test_load_delta_tree_no_such_timestamp(tmp_path: Path, request_context: None) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        serialize_tree(deserialize_tree({"inv": "attr-1"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        serialize_tree(deserialize_tree({"inv-2": "attr"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        serialize_tree(deserialize_tree({"inv": "attr-3"})),
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    with pytest.raises(MKGeneralException) as e:
        load_delta_tree(history_store, hostname, -1)
    assert "Found no history entry at the time of '-1' for the host 'inv-host'" == str(e.value)


def test_load_latest_delta_tree(tmp_path: Path, request_context: None) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "1",
        serialize_tree(deserialize_tree({"inv": "attr-1"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "2",
        serialize_tree(deserialize_tree({"inv-2": "attr"})),
    )
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "3",
        serialize_tree(deserialize_tree({"inv": "attr-3"})),
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    search_timestamp = int((tmp_path / "var/check_mk/inventory" / hostname).stat().st_mtime)

    delta_tree, corrupted_history_files = load_delta_tree(history_store, hostname, search_timestamp)

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0
    assert load_latest_delta_tree(history_store, hostname) is not None


def test_load_latest_delta_tree_no_archive_and_inv_tree(
    tmp_path: Path, request_context: None
) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    assert not load_latest_delta_tree(history_store, hostname)


def test_load_latest_delta_tree_one_archive_and_inv_tree(
    tmp_path: Path, request_context: None
) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )

    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    delta_tree = load_latest_delta_tree(history_store, hostname)

    assert delta_tree is not None


def test_load_latest_delta_tree_one_archive_and_no_inv_tree(
    tmp_path: Path, request_context: None
) -> None:
    history_store = HistoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )

    delta_tree = load_latest_delta_tree(history_store, hostname)

    assert delta_tree is not None
