#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.history import HistoryStore

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
    """Regression test for crash groups 3652/3629.

    The former _CachedDeltaTreeLoader.get_cached_entry() code path tried to deserialise
    old delta-cache files via ImmutableDeltaTree.deserialize() which raised
    KeyError: Attributes for pre-WK-18319 files.  That class and method were removed by
    WK-18319 which also introduced HistoryArchivePath so that history entries can be
    computed directly from archive trees without requiring a pre-existing delta cache.
    """
    host_name = HostName("hostname")
    for idx in range(3):
        tree = raw_tree(f"val-{idx}")
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", tree
        )

    # No delta cache files — history must still be computed from archives alone.
    history = HistoryStore(tmp_path).load(
        host_name,
        history_paths_filter=lambda paths: paths,
        delta_tree_filters=None,
    )
    assert len(history.entries) == 3
    assert not history.corrupted
