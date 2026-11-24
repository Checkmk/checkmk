#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from pathlib import Path

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.delta import SDDeltaValue
from cmk.inventory.filtering import SDFilterChoice
from cmk.inventory.history import History, HistoryStore
from cmk.inventory.serialization import SDRawDeltaTree, SDRawTree
from cmk.inventory.trees import SDKey, SDNodeName

from ._fixtures import gzipped_repr, raw_tree


def _save_legacy_archive_and_current_tree(tmp_path: Path) -> None:
    for idx in range(5):
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", raw_tree(f"val-{idx}")
        )
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)
    cmk.ccc.store.save_bytes_to_file(
        tmp_path / "var/check_mk/inventory/hostname.gz", gzipped_repr(tree)
    )


def test_load_history_of_legacy_files_lists_every_entry(tmp_path: Path) -> None:
    _save_legacy_archive_and_current_tree(tmp_path)

    history = HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert (len(history.entries), history.corrupted) == (6, [])


def test_load_history_leaves_the_legacy_files_in_place(tmp_path: Path) -> None:
    _save_legacy_archive_and_current_tree(tmp_path)

    HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert (
        sorted(p.name for p in (tmp_path / "var/check_mk/inventory").iterdir()),
        sorted(p.name for p in (tmp_path / "var/check_mk/inventory_archive/hostname").iterdir()),
    ) == (["hostname", "hostname.gz"], ["0", "1", "2", "3", "4"])


def test_load_history_caches_the_deltas_as_json(tmp_path: Path) -> None:
    _save_legacy_archive_and_current_tree(tmp_path)

    HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert {
        p.suffix for p in (tmp_path / "var/check_mk/inventory_delta_cache/hostname").iterdir()
    } == {".json"}


def test_load_history_only_from_archive_files(tmp_path: Path) -> None:
    for idx in range(3):
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", raw_tree(f"val-{idx}")
        )

    history = HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert (len(history.entries), history.corrupted) == (3, [])


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
        delta_tree_filters=None,
    )

    assert [(e.new, e.changed, e.removed) for e in history.entries] == [(1, 2, 3)]


def test_load_history_reports_a_delta_cache_file_with_an_unknown_name(tmp_path: Path) -> None:
    file_path = tmp_path / "var/check_mk/inventory_delta_cache/hostname/not-a-timestamp.json"
    cmk.ccc.store.save_text_to_file(file_path, "{}")

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        delta_tree_filters=None,
    )

    assert history.corrupted == ["inventory_delta_cache/hostname/not-a-timestamp.json"]


def test_load_history_reports_an_unreadable_delta_cache_file(tmp_path: Path) -> None:
    file_path = tmp_path / "var/check_mk/inventory_delta_cache/hostname/1_2.json"
    file_path.mkdir(parents=True)

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        delta_tree_filters=None,
    )

    assert history.corrupted == ["inventory_delta_cache/hostname/1_2.json"]


def test_load_history_reports_an_empty_legacy_delta_cache_file(tmp_path: Path) -> None:
    file_path = tmp_path / "var/check_mk/inventory_delta_cache/hostname/1_2"
    file_path.parent.mkdir(parents=True)
    file_path.touch()

    history = HistoryStore(tmp_path).load(
        HostName("hostname"),
        delta_tree_filters=None,
    )

    assert history.corrupted == ["inventory_delta_cache/hostname/1_2"]


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
        delta_tree_filters=[
            SDFilterChoice(path=(SDNodeName("node"),), pairs="all", columns="all", nodes="all")
        ],
    )

    assert [e.current_timestamp for e in history.entries] == [0]


def _save_archive(tmp_path: Path, count: int) -> None:
    for idx in range(count):
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", raw_tree(f"val-{idx}")
        )


def test_load_latest_delta_tree_is_the_one_of_the_newest_entry(tmp_path: Path) -> None:
    _save_archive(tmp_path, 3)

    assert HistoryStore(tmp_path).load_latest_delta_tree(
        HostName("hostname"), delta_tree_filters=None
    ).attributes.pairs == {SDKey("key"): SDDeltaValue(old="val-1", new="val-2")}


def test_load_latest_delta_tree_without_an_archive_is_empty(tmp_path: Path) -> None:
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree("val"))

    assert not HistoryStore(tmp_path).load_latest_delta_tree(
        HostName("hostname"), delta_tree_filters=None
    )


def test_load_delta_tree_at_a_timestamp_loads_its_entry(tmp_path: Path) -> None:
    _save_archive(tmp_path, 3)

    found = HistoryStore(tmp_path).load_delta_tree_at(
        HostName("hostname"), 1, delta_tree_filters=None
    )

    assert found is not None and (found[0].attributes.pairs, found[1]) == (
        {SDKey("key"): SDDeltaValue(old="val-0", new="val-1")},
        [],
    )


def test_load_delta_tree_at_an_unknown_timestamp_finds_nothing(tmp_path: Path) -> None:
    _save_archive(tmp_path, 3)

    assert (
        HistoryStore(tmp_path).load_delta_tree_at(HostName("hostname"), 5, delta_tree_filters=None)
        is None
    )


def test_load_history_of_a_host_without_history(tmp_path: Path) -> None:
    assert HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None) == History(
        entries=[], corrupted=[]
    )


def _save_archive_and_current_tree(tmp_path: Path) -> None:
    for idx, raw in enumerate(
        [{"inv": "attr-0"}, {"inv": "attr-1"}, {"inv-2": "attr"}, {"inv": "attr-3"}]
    ):
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", raw
        )
    current_tree = tmp_path / "var/check_mk/inventory/hostname"
    cmk.ccc.store.save_object_to_file(current_tree, {"inv": "attr"})
    os.utime(current_tree, (100, 100))


def test_load_history_counts_the_changes(tmp_path: Path) -> None:
    _save_archive_and_current_tree(tmp_path)

    history = HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert [(e.new, e.changed, e.removed) for e in history.entries] == [
        (1, 0, 0),
        (0, 1, 0),
        (1, 0, 1),
        (1, 0, 1),
        (0, 1, 0),
    ]


def test_load_history_caches_the_deltas_between_archived_trees(tmp_path: Path) -> None:
    _save_archive_and_current_tree(tmp_path)

    HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert sorted(
        fp.name for fp in (tmp_path / "var/check_mk/inventory_delta_cache/hostname").iterdir()
    ) == ["0_1.json", "1_2.json", "2_3.json", "None_0.json"]


def test_load_history_reports_an_archive_file_with_an_unknown_name(tmp_path: Path) -> None:
    archive_dir = tmp_path / "var/check_mk/inventory_archive/hostname"
    archive_dir.mkdir(parents=True)
    (archive_dir / "foo").touch()

    history = HistoryStore(tmp_path).load(HostName("hostname"), delta_tree_filters=None)

    assert history.corrupted == ["inventory_archive/hostname/foo"]
