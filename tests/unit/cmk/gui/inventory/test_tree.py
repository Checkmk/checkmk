#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import cmk.ccc.store
import cmk.gui.inventory
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.gui.inventory import (
    get_history,
    load_delta_tree,
    load_latest_delta_tree,
    load_tree,
    make_filter_choices_from_permitted_paths,
)
from cmk.gui.watolib.groups_io import PermittedPath
from cmk.inventory.structured_data import (
    deserialize_tree,
    HistoryStore,
    ImmutableTree,
    SDFilterChoice,
    SDKey,
    SDNodeName,
)


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        (
            {
                "visible_raw_path": "path.to.node",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": ("choices", ["node"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes=[SDNodeName("node")],
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns=[SDKey("key")],
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="nothing",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="nothing",
                columns="all",
                nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": "nothing",
            },
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="nothing",
                nodes="all",
            ),
        ),
    ],
)
def test_make_filter_choices_from_permitted_paths(
    entry: PermittedPath, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_permitted_paths([entry])[0] == expected_filter_choice


@pytest.mark.parametrize(
    "host_name, raw_status_data_tree, expected_tree",
    [
        (
            None,
            b"",
            deserialize_tree({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            b"",
            deserialize_tree({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            b"",
            deserialize_tree({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            b"{'deserialized': 'tree'}",
            deserialize_tree({"deserialized": "tree"}),
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_load_tree(
    monkeypatch: MonkeyPatch,
    host_name: HostName | None,
    raw_status_data_tree: bytes,
    expected_tree: ImmutableTree,
) -> None:
    monkeypatch.setattr(
        cmk.gui.inventory._tree,  # noqa: SLF001
        "_load_tree_from_file",
        (
            lambda *args, **kw: (  # noqa: ARG005
                deserialize_tree({"loaded": "tree"})
                if kw["tree_type"] == "status_data"
                else ImmutableTree()
            )
        ),
    )
    assert (
        load_tree(
            host_name=host_name,
            raw_status_data_tree=raw_status_data_tree,
        )
        == expected_tree
    )


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
