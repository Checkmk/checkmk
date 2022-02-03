#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Dict

import pytest

import cmk.utils
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.structured_data import StructuredDataNode

import cmk.gui.inventory


@pytest.mark.parametrize(
    "raw_path, expected_path",
    [
        ("", ([], None)),
        (".", ([], None)),
        (".hardware.", (["hardware"], None)),
        (".hardware.cpu.", (["hardware", "cpu"], None)),
        (".hardware.cpu.model", (["hardware", "cpu"], ["model"])),
        (".software.packages:", (["software", "packages"], [])),
        (".software.packages:17.name", (["software", "packages", "17"], ["name"])),
    ],
)
def test_parse_tree_path(raw_path, expected_path):
    assert cmk.gui.inventory.parse_tree_path(raw_path) == expected_path


@pytest.mark.parametrize(
    "hostname, row, expected_tree",
    [
        (None, {}, StructuredDataNode.deserialize({"loaded": "tree"})),
        ("hostname", {}, StructuredDataNode.deserialize({"loaded": "tree"})),
        (
            "hostname",
            {"host_structured_status": b""},
            StructuredDataNode.deserialize({"loaded": "tree"}),
        ),
        (
            "hostname",
            {"host_structured_status": b"{'deserialized': 'tree'}"},
            StructuredDataNode.deserialize({"deserialized": "tree"}),
        ),
    ],
)
def test__load_status_data_tree(monkeypatch, hostname, row, expected_tree):
    monkeypatch.setattr(
        cmk.gui.inventory,
        "_load_structured_data_tree",
        lambda t, hostname: StructuredDataNode.deserialize({"loaded": "tree"}),
    )
    status_data_tree = cmk.gui.inventory._load_status_data_tree(hostname, row)
    assert status_data_tree is not None
    assert status_data_tree.is_equal(expected_tree)


_InvTree = StructuredDataNode.deserialize({"inv": "node"})
_StatusDataTree = StructuredDataNode.deserialize({"status": "node"})
_MergedTree = StructuredDataNode.deserialize({"inv": "node", "status": "node"})


@pytest.mark.parametrize(
    "inventory_tree, status_data_tree, expected_tree",
    [
        (_InvTree, None, _InvTree),
        (None, _StatusDataTree, _StatusDataTree),
        (_InvTree, _StatusDataTree, _MergedTree),
    ],
)
def test__merge_inventory_and_status_data_tree(inventory_tree, status_data_tree, expected_tree):
    merged_tree = cmk.gui.inventory._merge_inventory_and_status_data_tree(
        inventory_tree,
        status_data_tree,
    )
    assert merged_tree is not None
    assert merged_tree.is_equal(expected_tree)


def test__merge_inventory_and_status_data_tree_both_None():
    merged_tree = cmk.gui.inventory._merge_inventory_and_status_data_tree(None, None)
    assert merged_tree is None


def test_get_history_empty():
    for hostname in [
        "inv-host",
        "/inv-host",
    ]:
        history, corrupted_history_files = cmk.gui.inventory.get_history(hostname)

        assert len(history) == 0
        assert len(corrupted_history_files) == 0


def test_get_history_archive_but_no_inv_tree():
    hostname = "inv-host"

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        StructuredDataNode.deserialize({"inv": "attr-0"}).serialize(),
    )

    history, corrupted_history_files = cmk.gui.inventory.get_history(hostname)

    assert len(history) == 1
    assert len(corrupted_history_files) == 0


@pytest.fixture(name="create_inventory_history")
def _create_inventory_history() -> None:
    hostname = "inv-host"

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        StructuredDataNode.deserialize({"inv": "attr-0"}).serialize(),
    )
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "1"),
        StructuredDataNode.deserialize({"inv": "attr-1"}).serialize(),
    )
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "2"),
        StructuredDataNode.deserialize({"inv-2": "attr"}).serialize(),
    )
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "3"),
        StructuredDataNode.deserialize({"inv": "attr-3"}).serialize(),
    )
    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        StructuredDataNode.deserialize({"inv": "attr"}).serialize(),
    )


@pytest.mark.usefixtures("create_inventory_history")
def test_get_history() -> None:
    hostname = "inv-host"
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
    expected_raw_delta_tree: Dict,
) -> None:
    hostname = "inv-host"
    expected_delta_tree = StructuredDataNode.deserialize(expected_raw_delta_tree)

    delta_tree, corrupted_history_files = cmk.gui.inventory.load_delta_tree(
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert delta_tree.is_equal(expected_delta_tree)
    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("create_inventory_history")
def test_load_delta_tree_no_such_timestamp():
    hostname = "inv-host"
    with pytest.raises(MKGeneralException) as e:
        cmk.gui.inventory.load_delta_tree(hostname, -1)
    assert "Found no history entry at the time of '-1' for the host 'inv-host'" == str(e.value)


@pytest.mark.usefixtures("create_inventory_history")
def test_load_latest_delta_tree() -> None:
    hostname = "inv-host"
    expected_delta_tree = StructuredDataNode.deserialize({"inv": ("attr-3", "attr")})
    search_timestamp = int(Path(cmk.utils.paths.inventory_output_dir, hostname).stat().st_mtime)

    delta_tree, corrupted_history_files = cmk.gui.inventory.load_delta_tree(
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert delta_tree.is_equal(expected_delta_tree)
    assert len(corrupted_history_files) == 0

    delta_tree_2 = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree_2 is not None
    assert delta_tree_2.is_equal(expected_delta_tree)


def test_load_latest_delta_tree_no_archive_and_inv_tree() -> None:
    hostname = "inv-host"

    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        StructuredDataNode.deserialize({"inv": "attr"}).serialize(),
    )

    delta_tree = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree is None


def test_load_latest_delta_tree_one_archive_and_inv_tree() -> None:
    hostname = "inv-host"
    expected_delta_tree = StructuredDataNode.deserialize({"inv": ("attr-0", "attr")})

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        StructuredDataNode.deserialize({"inv": "attr-0"}).serialize(),
    )

    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        StructuredDataNode.deserialize({"inv": "attr"}).serialize(),
    )

    delta_tree = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree is not None
    assert delta_tree.is_equal(expected_delta_tree)


def test_load_latest_delta_tree_one_archive_and_no_inv_tree() -> None:
    hostname = "inv-host"
    expected_delta_tree = StructuredDataNode.deserialize({"inv": (None, "attr-0")})

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        StructuredDataNode.deserialize({"inv": "attr-0"}).serialize(),
    )

    delta_tree = cmk.gui.inventory.load_latest_delta_tree(hostname)

    assert delta_tree is not None
    assert delta_tree.is_equal(expected_delta_tree)
