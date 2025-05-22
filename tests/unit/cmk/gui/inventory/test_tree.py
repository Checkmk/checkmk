#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import cmk.ccc.store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import (
    deserialize_tree,
    ImmutableTree,
    InventoryStore,
    SDFilterChoice,
    SDKey,
    SDNodeName,
)

import cmk.gui.inventory
from cmk.gui.inventory._tree import (
    _make_filter_choices_from_permitted_paths,
    get_history,
    InventoryPath,
    load_delta_tree,
    load_latest_delta_tree,
    load_tree,
    make_filter_choices_from_api_request_paths,
    parse_internal_raw_path,
    TreeSource,
)
from cmk.gui.watolib.groups_io import PermittedPath


@pytest.mark.parametrize(
    "raw_path, expected_path, expected_node_name",
    [
        (
            "",
            InventoryPath(
                path=tuple(),
                source=TreeSource.node,
            ),
            "",
        ),
        (
            ".",
            InventoryPath(
                path=tuple(),
                source=TreeSource.node,
            ),
            "",
        ),
        (
            ".hardware.",
            InventoryPath(
                path=(SDNodeName("hardware"),),
                source=TreeSource.node,
            ),
            "hardware",
        ),
        (
            ".hardware.cpu.",
            InventoryPath(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                source=TreeSource.node,
            ),
            "cpu",
        ),
        (
            ".hardware.cpu.model",
            InventoryPath(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                source=TreeSource.attributes,
                key=SDKey("model"),
            ),
            "cpu",
        ),
        (
            ".software.packages:",
            InventoryPath(
                path=(SDNodeName("software"), SDNodeName("packages")),
                source=TreeSource.table,
            ),
            "packages",
        ),
        (
            ".hardware.memory.arrays:*.",
            InventoryPath(
                (
                    SDNodeName("hardware"),
                    SDNodeName("memory"),
                    SDNodeName("arrays"),
                    SDNodeName("*"),
                ),
                source=TreeSource.node,
            ),
            "*",
        ),
        (
            ".software.packages:17.name",
            InventoryPath(
                path=(SDNodeName("software"), SDNodeName("packages")),
                source=TreeSource.table,
                key=SDKey("name"),
            ),
            "packages",
        ),
        (
            ".software.packages:*.name",
            InventoryPath(
                path=(SDNodeName("software"), SDNodeName("packages")),
                source=TreeSource.table,
                key=SDKey("name"),
            ),
            "packages",
        ),
        (
            ".hardware.memory.arrays:*.devices:*.speed",
            InventoryPath(
                path=(
                    SDNodeName("hardware"),
                    SDNodeName("memory"),
                    SDNodeName("arrays"),
                    SDNodeName("*"),
                    SDNodeName("devices"),
                ),
                source=TreeSource.table,
                key=SDKey("speed"),
            ),
            "devices",
        ),
        (
            ".path:*.to.node.key",
            InventoryPath(
                path=(SDNodeName("path"), SDNodeName("*"), SDNodeName("to"), SDNodeName("node")),
                source=TreeSource.attributes,
                key=SDKey("key"),
            ),
            "node",
        ),
    ],
)
def test_parse_tree_path(
    raw_path: str, expected_path: InventoryPath, expected_node_name: str
) -> None:
    inventory_path = parse_internal_raw_path(raw_path)
    assert inventory_path == expected_path
    assert inventory_path.node_name == expected_node_name


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
def test__make_filter_choices_from_permitted_paths(
    entry: PermittedPath, expected_filter_choice: SDFilterChoice
) -> None:
    assert _make_filter_choices_from_permitted_paths([entry])[0] == expected_filter_choice


@pytest.mark.parametrize(
    "entry, expected_filter_choice",
    [
        # Tuple format
        (
            ".path.to.node.",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs="all",
                columns="all",
                nodes="all",
            ),
        ),
        (
            ".path.to.node:*.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
        (
            ".path.to.node.key",
            SDFilterChoice(
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                pairs=[SDKey("key")],
                columns=[SDKey("key")],
                nodes="nothing",
            ),
        ),
    ],
)
def test__make_filter_choices_from_api_request_paths(
    entry: str, expected_filter_choice: SDFilterChoice
) -> None:
    assert make_filter_choices_from_api_request_paths([entry])[0] == expected_filter_choice


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
def test_load_tree(
    monkeypatch: MonkeyPatch,
    host_name: HostName | None,
    raw_status_data_tree: bytes,
    expected_tree: ImmutableTree,
    request_context: None,
) -> None:
    monkeypatch.setattr(
        cmk.gui.inventory._tree,
        "_load_tree_from_file",
        (
            lambda *args, **kw: (
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


def test_get_history_empty(tmp_path: Path, request_context: None) -> None:
    history, corrupted_history_files = get_history(
        InventoryStore(tmp_path),
        HostName("inv-host"),
    )
    assert len(history) == 0
    assert len(corrupted_history_files) == 0


def test_get_history_archive_but_no_inv_tree(tmp_path: Path, request_context: None) -> None:
    inv_store = InventoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )

    history, corrupted_history_files = get_history(inv_store, hostname)

    assert len(history) == 1
    assert len(corrupted_history_files) == 0


def test_get_history(tmp_path: Path, request_context: None) -> None:
    inv_store = InventoryStore(tmp_path)
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

    history, corrupted_history_files = get_history(inv_store, hostname)

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
            ]
        ),
        sorted(
            [
                "0_1.json",
                "1_2.json",
                "2_3.json",
                "3_100.json",
                "None_0.json",
            ]
        ),
    ):
        assert delta_cache_filename == expected_delta_cache_filename


def test_get_history_corrupted_files(tmp_path: Path, request_context: None) -> None:
    inv_store = InventoryStore(tmp_path)
    hostname = HostName("inv-host")
    archive_dir = tmp_path / "var/check_mk/inventory_archive" / hostname
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "foo").touch()

    history, corrupted_history_files = get_history(inv_store, hostname)
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
    inv_store = InventoryStore(tmp_path)
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

    delta_tree, corrupted_history_files = load_delta_tree(
        inv_store,
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0


def test_load_delta_tree_no_such_timestamp(tmp_path: Path, request_context: None) -> None:
    inv_store = InventoryStore(tmp_path)
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
        load_delta_tree(inv_store, hostname, -1)
    assert "Found no history entry at the time of '-1' for the host 'inv-host'" == str(e.value)


def test_load_latest_delta_tree(tmp_path: Path, request_context: None) -> None:
    inv_store = InventoryStore(tmp_path)
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

    delta_tree, corrupted_history_files = load_delta_tree(inv_store, hostname, search_timestamp)

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0
    assert load_latest_delta_tree(inv_store, hostname) is not None


def test_load_latest_delta_tree_no_archive_and_inv_tree(
    tmp_path: Path, request_context: None
) -> None:
    inv_store = InventoryStore(tmp_path)
    hostname = HostName("inv-host")

    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    assert not load_latest_delta_tree(inv_store, hostname)


def test_load_latest_delta_tree_one_archive_and_inv_tree(
    tmp_path: Path, request_context: None
) -> None:
    inv_store = InventoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )

    # current tree
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory" / hostname,
        {"inv": "attr"},
    )

    delta_tree = load_latest_delta_tree(inv_store, hostname)

    assert delta_tree is not None


def test_load_latest_delta_tree_one_archive_and_no_inv_tree(
    tmp_path: Path, request_context: None
) -> None:
    inv_store = InventoryStore(tmp_path)
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive" / hostname / "0",
        {"inv": "attr-0"},
    )

    delta_tree = load_latest_delta_tree(inv_store, hostname)

    assert delta_tree is not None
