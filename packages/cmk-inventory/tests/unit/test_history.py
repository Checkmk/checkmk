#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.filtering import SDFilterChoice
from cmk.inventory.history import HistoryStore
from cmk.inventory.serialization import SDRawDeltaTree, SDRawTree
from cmk.inventory.trees import SDKey, SDNodeName

from ._fixtures import gzipped_repr, raw_tree


def test_load_history(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    for idx in range(5):
        tree = raw_tree(f"val-{idx}")
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", tree
        )
    tree = raw_tree("val")
    gzipped = gzipped_repr(tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    history = HistoryStore(tmp_path).load(
        host_name,
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )
    assert len(history.entries) == 6
    assert not history.corrupted
    assert (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()

    archive_file_paths = list((tmp_path / "var/check_mk/inventory_archive/hostname").iterdir())
    assert archive_file_paths
    for archive_file_path in archive_file_paths:
        assert archive_file_path.suffixes == []

    delta_cache_file_paths = list(
        (tmp_path / "var/check_mk/inventory_delta_cache/hostname").iterdir()
    )
    assert delta_cache_file_paths
    for delta_cache_file_path in delta_cache_file_paths:
        assert delta_cache_file_path.suffixes == [".json"]


def test_load_history_only_from_archive_files(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    for idx in range(3):
        tree = raw_tree(f"val-{idx}")
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", tree
        )

    history = HistoryStore(tmp_path).load(
        host_name,
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )
    assert len(history.entries) == 3
    assert not history.corrupted


def test_load_history_reads_the_counts_from_the_delta_cache(tmp_path: Path) -> None:
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory_delta_cache/hostname/None_123.json",
        json.dumps(
            (
                1,
                2,
                3,
                SDRawDeltaTree(
                    Attributes={"Pairs": {SDKey("key"): (None, "value")}}, Table={}, Nodes={}
                ),
            )
        ),
    )

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )

    assert [(e.new, e.changed, e.removed) for e in history.entries] == [(1, 2, 3)]


def test_load_history_reports_a_delta_cache_file_with_an_unknown_name(tmp_path: Path) -> None:
    file_path = tmp_path / "var/check_mk/inventory_delta_cache/hostname/not-a-timestamp.json"
    cmk.ccc.store.save_text_to_file(file_path, "{}")

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )

    assert list(history.corrupted) == [file_path]


def test_load_history_reports_an_unreadable_delta_cache_file(tmp_path: Path) -> None:
    file_path = tmp_path / "var/check_mk/inventory_delta_cache/hostname/1_2.json"
    file_path.mkdir(parents=True)

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )

    assert list(history.corrupted) == [file_path]


def test_load_history_reports_an_empty_legacy_delta_cache_file(tmp_path: Path) -> None:
    file_path = tmp_path / "var/check_mk/inventory_delta_cache/hostname/1_2"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )

    assert list(history.corrupted) == [file_path]


def _raw_tree_with_other_node(value: str) -> SDRawTree:
    return SDRawTree(
        Attributes={},
        Table={},
        Nodes={
            SDNodeName("node"): SDRawTree(
                Attributes={"Pairs": {SDKey("key"): "fixed"}}, Table={}, Nodes={}
            ),
            SDNodeName("other"): SDRawTree(
                Attributes={"Pairs": {SDKey("key"): value}}, Table={}, Nodes={}
            ),
        },
    )


def test_load_history_drops_the_entries_without_filtered_changes(tmp_path: Path) -> None:
    for idx in range(2):
        cmk.ccc.store.save_text_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}.json",
            json.dumps(_raw_tree_with_other_node(f"val-{idx}")),
        )

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=[
            SDFilterChoice(path=(SDNodeName("node"),), pairs="all", columns="all", nodes="all")
        ],
    )

    assert [e.current_timestamp for e in history.entries] == [0]
