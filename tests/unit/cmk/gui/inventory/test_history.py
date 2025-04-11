#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import deserialize_tree, serialize_tree

from cmk.gui.inventory._history import get_history, load_delta_tree, load_latest_delta_tree


def test_get_history_empty(request_context: None) -> None:
    history, corrupted_history_files = get_history(HostName("inv-host"))

    assert len(history) == 0
    assert len(corrupted_history_files) == 0


def test_get_history_archive_but_no_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )

    history, corrupted_history_files = get_history(hostname)

    assert len(history) == 1
    assert len(corrupted_history_files) == 0


@pytest.fixture(name="create_inventory_history")
def _create_inventory_history() -> None:
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "1"),
        serialize_tree(deserialize_tree({"inv": "attr-1"})),
    )
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "2"),
        serialize_tree(deserialize_tree({"inv-2": "attr"})),
    )
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "3"),
        serialize_tree(deserialize_tree({"inv": "attr-3"})),
    )
    # current tree
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        serialize_tree(deserialize_tree({"inv": "attr"})),
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


def test_get_history_corrupted_files(request_context: None) -> None:
    hostname = HostName("inv-host")
    archive_dir = Path(cmk.utils.paths.inventory_archive_dir, hostname)
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "foo").touch()

    history, corrupted_history_files = get_history(hostname)
    assert not history
    assert corrupted_history_files == ["var/check_mk/inventory_archive/inv-host/foo"]


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
def test_load_delta_tree_no_such_timestamp(request_context: None) -> None:
    hostname = HostName("inv-host")
    with pytest.raises(MKGeneralException) as e:
        load_delta_tree(hostname, -1)
    assert "Found no history entry at the time of '-1' for the host 'inv-host'" == str(e.value)


@pytest.mark.usefixtures("create_inventory_history")
def test_load_latest_delta_tree(request_context: None) -> None:
    hostname = HostName("inv-host")
    search_timestamp = int(Path(cmk.utils.paths.inventory_output_dir, hostname).stat().st_mtime)

    delta_tree, corrupted_history_files = load_delta_tree(hostname, search_timestamp)

    assert delta_tree is not None
    assert len(corrupted_history_files) == 0
    assert load_latest_delta_tree(hostname) is not None


def test_load_latest_delta_tree_no_archive_and_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # current tree
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    assert not load_latest_delta_tree(hostname)


def test_load_latest_delta_tree_one_archive_and_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )

    # current tree
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_output_dir, hostname),
        serialize_tree(deserialize_tree({"inv": "attr"})),
    )

    delta_tree = load_latest_delta_tree(hostname)

    assert delta_tree is not None


def test_load_latest_delta_tree_one_archive_and_no_inv_tree(request_context: None) -> None:
    hostname = HostName("inv-host")

    # history
    cmk.ccc.store.save_object_to_file(
        Path(cmk.utils.paths.inventory_archive_dir, hostname, "0"),
        serialize_tree(deserialize_tree({"inv": "attr-0"})),
    )

    delta_tree = load_latest_delta_tree(hostname)

    assert delta_tree is not None
