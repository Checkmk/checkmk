#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest import MonkeyPatch

import cmk.utils
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import ImmutableTree, SDFilterChoice

import cmk.gui.inventory
from cmk.gui.inventory import (
    _make_filter_choices_from_api_request_paths,
    _make_filter_choices_from_permitted_paths,
    InventoryPath,
    PermittedPath,
    TreeSource,
)
from cmk.gui.type_defs import Row


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
                path=("hardware",),
                source=TreeSource.node,
            ),
            "hardware",
        ),
        (
            ".hardware.cpu.",
            InventoryPath(
                path=("hardware", "cpu"),
                source=TreeSource.node,
            ),
            "cpu",
        ),
        (
            ".hardware.cpu.model",
            InventoryPath(
                path=("hardware", "cpu"),
                source=TreeSource.attributes,
                key="model",
            ),
            "cpu",
        ),
        (
            ".software.packages:",
            InventoryPath(
                path=("software", "packages"),
                source=TreeSource.table,
            ),
            "packages",
        ),
        (
            ".hardware.memory.arrays:*.",
            InventoryPath(
                ("hardware", "memory", "arrays", "*"),
                source=TreeSource.node,
            ),
            "*",
        ),
        (
            ".software.packages:17.name",
            InventoryPath(
                path=("software", "packages"),
                source=TreeSource.table,
                key="name",
            ),
            "packages",
        ),
        (
            ".software.packages:*.name",
            InventoryPath(
                path=("software", "packages"),
                source=TreeSource.table,
                key="name",
            ),
            "packages",
        ),
        (
            ".hardware.memory.arrays:*.devices:*.speed",
            InventoryPath(
                path=("hardware", "memory", "arrays", "*", "devices"),
                source=TreeSource.table,
                key="speed",
            ),
            "devices",
        ),
        (
            ".path:*.to.node.key",
            InventoryPath(
                path=("path", "*", "to", "node"),
                source=TreeSource.attributes,
                key="key",
            ),
            "node",
        ),
    ],
)
def test_parse_tree_path(
    raw_path: str, expected_path: InventoryPath, expected_node_name: str
) -> None:
    inventory_path = InventoryPath.parse(raw_path)
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
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns="all",
                choice_nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": ("choices", ["node"]),
            },
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns="all",
                choice_nodes=["node"],
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs=["key"],
                choice_columns="all",
                choice_nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": ("choices", ["key"]),
            },
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns=["key"],
                choice_nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "nodes": "nothing",
            },
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns="all",
                choice_nodes="nothing",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "attributes": "nothing",
            },
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs="nothing",
                choice_columns="all",
                choice_nodes="all",
            ),
        ),
        (
            {
                "visible_raw_path": "path.to.node",
                "columns": "nothing",
            },
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns="nothing",
                choice_nodes="all",
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
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns="all",
                choice_nodes="all",
            ),
        ),
        (
            ".path.to.node:",
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs="all",
                choice_columns="all",
                choice_nodes="all",
            ),
        ),
        (
            ".path.to.node:*.key",
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs=["key"],
                choice_columns=["key"],
                choice_nodes="nothing",
            ),
        ),
        (
            ".path.to.node.key",
            SDFilterChoice(
                path=("path", "to", "node"),
                choice_pairs=["key"],
                choice_columns=["key"],
                choice_nodes="nothing",
            ),
        ),
    ],
)
def test__make_filter_choices_from_api_request_paths(
    entry: str, expected_filter_choice: SDFilterChoice
) -> None:
    assert _make_filter_choices_from_api_request_paths([entry])[0] == expected_filter_choice


@pytest.mark.parametrize(
    "hostname, row, expected_tree",
    [
        (
            None,
            {},
            ImmutableTree.deserialize({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            {},
            ImmutableTree.deserialize({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            {"host_structured_status": b""},
            ImmutableTree.deserialize({"loaded": "tree"}),
        ),
        (
            HostName("hostname"),
            {"host_structured_status": b"{'deserialized': 'tree'}"},
            ImmutableTree.deserialize({"deserialized": "tree"}),
        ),
    ],
)
def test_load_filtered_and_merged_tree(
    monkeypatch: MonkeyPatch, hostname: HostName | None, row: Row, expected_tree: ImmutableTree
) -> None:
    monkeypatch.setattr(
        cmk.gui.inventory,
        "_load_tree_from_file",
        (
            lambda *args, **kw: ImmutableTree.deserialize({"loaded": "tree"})
            if kw["tree_type"] == "status_data"
            else ImmutableTree()
        ),
    )
    row.update({"host_name": hostname})
    assert cmk.gui.inventory.load_filtered_and_merged_tree(row) == expected_tree


def test_get_history_empty() -> None:
    for hostname in [
        HostName("inv-host"),
        HostName("/inv-host"),
    ]:
        history, corrupted_history_files = cmk.gui.inventory.get_history(hostname)

        assert len(history) == 0
        assert len(corrupted_history_files) == 0


def test_get_history_archive_but_no_inv_tree() -> None:
    hostname = HostName("inv-host")

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        ImmutableTree.deserialize({"inv": "attr-0"}).serialize(),
    )

    history, corrupted_history_files = cmk.gui.inventory.get_history(hostname)

    assert len(history) == 1
    assert len(corrupted_history_files) == 0


@pytest.fixture(name="create_inventory_history")
def _create_inventory_history() -> None:
    hostname = HostName("inv-host")

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        ImmutableTree.deserialize({"inv": "attr-0"}).serialize(),
    )
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "1"),
        ImmutableTree.deserialize({"inv": "attr-1"}).serialize(),
    )
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "2"),
        ImmutableTree.deserialize({"inv-2": "attr"}).serialize(),
    )
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "3"),
        ImmutableTree.deserialize({"inv": "attr-3"}).serialize(),
    )
    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        ImmutableTree.deserialize({"inv": "attr"}).serialize(),
    )


@pytest.mark.usefixtures("create_inventory_history")
def test_get_history() -> None:
    hostname = HostName("inv-host")
    expected_results = [
        (1, 0, 0),
        (0, 1, 0),
        (1, 0, 1),
        (1, 0, 1),
        (0, 1, 0),
    ]

    history, corrupted_history_files = cmk.gui.inventory.get_history(hostname)

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
                for fp in Path(
                    cmk.utils.paths.inventory_delta_cache_dir,
                    hostname,
                ).iterdir()
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


@pytest.mark.usefixtures("create_inventory_history")
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
    search_timestamp: int,
    expected_raw_delta_tree: dict,
) -> None:
    hostname = HostName("inv-host")

    delta_tree, corrupted_history_files = cmk.gui.inventory.load_delta_tree(
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("create_inventory_history")
def test_load_delta_tree_no_such_timestamp() -> None:
    hostname = HostName("inv-host")
    with pytest.raises(MKGeneralException) as e:
        cmk.gui.inventory.load_delta_tree(hostname, -1)
    assert "Found no history entry at the time of '-1' for the host 'inv-host'" == str(e.value)


@pytest.mark.usefixtures("create_inventory_history")
def test_load_latest_delta_tree() -> None:
    hostname = HostName("inv-host")
    search_timestamp = int(Path(cmk.utils.paths.inventory_output_dir, hostname).stat().st_mtime)

    delta_tree, corrupted_history_files = cmk.gui.inventory.load_delta_tree(
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0

    delta_tree_2 = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree_2 is not None


def test_load_latest_delta_tree_no_archive_and_inv_tree() -> None:
    hostname = HostName("inv-host")

    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        ImmutableTree.deserialize({"inv": "attr"}).serialize(),
    )

    assert not cmk.gui.inventory.load_latest_delta_tree(hostname)


def test_load_latest_delta_tree_one_archive_and_inv_tree() -> None:
    hostname = HostName("inv-host")

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        ImmutableTree.deserialize({"inv": "attr-0"}).serialize(),
    )

    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        ImmutableTree.deserialize({"inv": "attr"}).serialize(),
    )

    delta_tree = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree is not None


def test_load_latest_delta_tree_one_archive_and_no_inv_tree() -> None:
    hostname = HostName("inv-host")

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        ImmutableTree.deserialize({"inv": "attr-0"}).serialize(),
    )

    delta_tree = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree is not None
