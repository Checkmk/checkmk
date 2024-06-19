#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.utils
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import ImmutableTree

from cmk.gui.inventory._history import get_history, load_delta_tree, load_latest_delta_tree


def test_get_history_empty() -> None:
    history, corrupted_history_files = get_history(HostName("inv-host"))

    assert len(history) == 0
    assert len(corrupted_history_files) == 0


def test_get_history_archive_but_no_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        ImmutableTree.deserialize({"inv": "attr-0"}).serialize(),
    )

    history, corrupted_history_files = get_history(hostname)

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
def test_get_history(request_context: None) -> None:
    hostname = HostName("inv-host")
    expected_results = [
        (1, 0, 0),
        (0, 1, 0),
        (1, 0, 1),
        (1, 0, 1),
        (0, 1, 0),
    ]

    history, corrupted_history_files = get_history(hostname)

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
    request_context: None,
) -> None:
    hostname = HostName("inv-host")

    delta_tree, corrupted_history_files = load_delta_tree(
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0


@pytest.mark.usefixtures("create_inventory_history")
def test_load_delta_tree_no_such_timestamp() -> None:
    hostname = HostName("inv-host")
    with pytest.raises(MKGeneralException) as e:
        load_delta_tree(hostname, -1)
    assert "Found no history entry at the time of '-1' for the host 'inv-host'" == str(e.value)


@pytest.mark.usefixtures("create_inventory_history")
def test_load_latest_delta_tree(request_context: None) -> None:
    hostname = HostName("inv-host")
    search_timestamp = int(Path(cmk.utils.paths.inventory_output_dir, hostname).stat().st_mtime)

    delta_tree, corrupted_history_files = load_delta_tree(
        hostname,
        search_timestamp,
    )

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0

    delta_tree_2 = load_latest_delta_tree(hostname)

    assert delta_tree_2 is not None


def test_load_latest_delta_tree_no_archive_and_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # current tree
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        ImmutableTree.deserialize({"inv": "attr"}).serialize(),
    )

    assert not load_latest_delta_tree(hostname)


def test_load_latest_delta_tree_one_archive_and_inv_tree(request_context: None) -> None:
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

    delta_tree = load_latest_delta_tree(hostname)

    assert delta_tree is not None


def test_load_latest_delta_tree_one_archive_and_no_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # history
    cmk.utils.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        ImmutableTree.deserialize({"inv": "attr-0"}).serialize(),
    )

    delta_tree = load_latest_delta_tree(hostname)

    assert delta_tree is not None
