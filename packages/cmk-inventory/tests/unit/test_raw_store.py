#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from pathlib import Path

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.raw_store import RawInventoryStore, rename
from cmk.inventory.serialization import (
    make_meta,
    parse_from_gzipped,
    SDMetaAndRawTree,
)

from ._fixtures import gzipped_json, gzipped_repr, raw_tree


def _host_files(tmp_path: Path, host_name: HostName, suffix: str) -> Sequence[Path]:
    return [
        tmp_path / f"var/check_mk/inventory/{host_name}{suffix}",
        tmp_path / f"var/check_mk/inventory/{host_name}{suffix}.gz",
        tmp_path / f"tmp/check_mk/status_data/{host_name}{suffix}",
        *(
            tmp_path / f"var/check_mk/inventory_archive/{host_name}/{idx}{suffix}"
            for idx in range(5)
        ),
        *(
            tmp_path / f"var/check_mk/inventory_delta_cache/{host_name}/{prev}_{prev + 1}{suffix}"
            for prev in range(4)
        ),
    ]


def test_rename_legacy(tmp_path: Path) -> None:
    old_host_name = HostName("old_host_name")
    tree = raw_tree("val")
    gzipped = gzipped_repr(tree)
    cmk.ccc.store.save_object_to_file(tmp_path / f"var/check_mk/inventory/{old_host_name}", tree)
    cmk.ccc.store.save_bytes_to_file(
        tmp_path / f"var/check_mk/inventory/{old_host_name}.gz", gzipped
    )
    cmk.ccc.store.save_object_to_file(tmp_path / f"tmp/check_mk/status_data/{old_host_name}", tree)
    timestamps = list(range(5))
    for idx in timestamps:
        tree = raw_tree(f"val-{idx}")
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/{old_host_name}/{idx}", tree
        )
    for prev, cur in zip(timestamps, timestamps[1:]):
        tree = raw_tree(f"val-{prev}-{cur}")
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}/{prev}_{cur}", tree
        )

    new_host_name = HostName("new_host_name")
    rename(tmp_path, old_host_name=old_host_name, new_host_name=new_host_name)

    old_files = _host_files(tmp_path, old_host_name, "")
    new_files = _host_files(tmp_path, new_host_name, "")
    assert (
        [p.exists() for p in old_files],
        [p.exists() for p in new_files],
        (tmp_path / f"var/check_mk/inventory_archive/{old_host_name}").exists(),
        (tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}").exists(),
    ) == ([False] * len(old_files), [True] * len(new_files), False, False)


def test_rename(tmp_path: Path) -> None:
    old_host_name = HostName("old_host_name")
    tree = raw_tree("val")
    gzipped = gzipped_json(tree)
    cmk.ccc.store.save_text_to_file(
        tmp_path / f"var/check_mk/inventory/{old_host_name}.json", json.dumps(tree)
    )
    cmk.ccc.store.save_bytes_to_file(
        tmp_path / f"var/check_mk/inventory/{old_host_name}.json.gz", gzipped
    )
    cmk.ccc.store.save_text_to_file(
        tmp_path / f"tmp/check_mk/status_data/{old_host_name}.json", json.dumps(tree)
    )
    timestamps = list(range(5))
    for idx in timestamps:
        tree = raw_tree(f"val-{idx}")
        cmk.ccc.store.save_text_to_file(
            tmp_path / f"var/check_mk/inventory_archive/{old_host_name}/{idx}.json",
            json.dumps(tree),
        )
    for prev, cur in zip(timestamps, timestamps[1:]):
        tree = raw_tree(f"val-{prev}-{cur}")
        cmk.ccc.store.save_text_to_file(
            tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}/{prev}_{cur}.json",
            json.dumps(tree),
        )

    new_host_name = HostName("new_host_name")
    rename(tmp_path, old_host_name=old_host_name, new_host_name=new_host_name)

    old_files = _host_files(tmp_path, old_host_name, ".json")
    new_files = _host_files(tmp_path, new_host_name, ".json")
    assert (
        [p.exists() for p in old_files],
        [p.exists() for p in new_files],
        (tmp_path / f"var/check_mk/inventory_archive/{old_host_name}").exists(),
        (tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}").exists(),
    ) == ([False] * len(old_files), [True] * len(new_files), False, False)


def _save_meta_and_raw_inventory_tree(tmp_path: Path, timestamp: int) -> SDMetaAndRawTree:
    meta_and_raw_tree = SDMetaAndRawTree(meta=make_meta(do_archive=True), raw_tree=raw_tree("val"))
    RawInventoryStore(tmp_path).save_meta_and_raw_inventory_tree(
        host_name=HostName("hostname"),
        meta_and_raw_tree=meta_and_raw_tree,
        timestamp=timestamp,
    )
    return meta_and_raw_tree


def test_save_meta_and_raw_inventory_tree_dates_the_tree(tmp_path: Path) -> None:
    _save_meta_and_raw_inventory_tree(tmp_path, 123456)
    assert (tmp_path / "var/check_mk/inventory/hostname.json").stat().st_mtime == 123456


def test_save_meta_and_raw_inventory_tree_dates_the_gzipped_tree(tmp_path: Path) -> None:
    _save_meta_and_raw_inventory_tree(tmp_path, 123456)
    assert (tmp_path / "var/check_mk/inventory/hostname.json.gz").stat().st_mtime == 123456


def test_save_meta_and_raw_inventory_tree_is_read_back_from_the_gzipped_tree(
    tmp_path: Path,
) -> None:
    meta_and_raw_tree = _save_meta_and_raw_inventory_tree(tmp_path, 123456)
    assert (
        parse_from_gzipped((tmp_path / "var/check_mk/inventory/hostname.json.gz").read_bytes())
        == meta_and_raw_tree
    )


def test_rename_without_history_reports_only_the_renamed_trees(tmp_path: Path) -> None:
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/old_host_name.json", json.dumps(raw_tree("val"))
    )

    actions = rename(
        tmp_path, old_host_name=HostName("old_host_name"), new_host_name=HostName("new_host_name")
    )

    assert list(actions) == ["inv"]


def test_raw_store_archives_the_tree_dated_by_its_remote_timestamp(tmp_path: Path) -> None:
    _save_meta_and_raw_inventory_tree(tmp_path, 123)

    RawInventoryStore(tmp_path).archive_inventory_tree(host_name=HostName("hostname"), debug=False)

    assert list((tmp_path / "var/check_mk/inventory_archive/hostname").iterdir()) == [
        tmp_path / "var/check_mk/inventory_archive/hostname/123.json"
    ]
