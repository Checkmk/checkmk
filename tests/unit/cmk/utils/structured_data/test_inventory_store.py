#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
import json
from pathlib import Path

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName

from cmk.utils.structured_data import (
    deserialize_tree,
    InventoryStore,
    load_history,
    make_meta,
    SDKey,
    SDMetaAndRawTree,
    SDNodeName,
    SDRawTree,
)


def _raw_tree(value: str) -> SDRawTree:
    return SDRawTree(
        Attributes={"Pairs": {SDKey("key"): value}},
        Table={
            "KeyColumns": [SDKey("col1")],
            "Rows": [
                {SDKey("col1"): "val11", SDKey("col2"): "val12"},
                {SDKey("col1"): "val21", SDKey("col2"): "val22"},
            ],
        },
        Nodes={
            SDNodeName("node"): SDRawTree(
                Attributes={"Pairs": {SDKey("nkey"): "nval"}},
                Table={
                    "KeyColumns": [SDKey("ncol1")],
                    "Rows": [
                        {SDKey("ncol1"): "nval11", SDKey("ncol2"): "nval12"},
                        {SDKey("ncol1"): "nval21", SDKey("ncol2"): "nval22"},
                    ],
                },
                Nodes={},
            ),
        },
    )


def _gzipped_repr(raw_tree: SDRawTree) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(
            (
                repr(SDMetaAndRawTree(meta=make_meta(do_archive=False), raw_tree=raw_tree)) + "\n"
            ).encode("utf-8")
        )
    return buf.getvalue()


def _gzipped_json(raw_tree: SDRawTree) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write(
            (
                json.dumps(SDMetaAndRawTree(meta=make_meta(do_archive=False), raw_tree=raw_tree))
                + "\n"
            ).encode("utf-8")
        )
    return buf.getvalue()


def test_load_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree)

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_inventory_tree(host_name=host_name) == deserialize_tree(raw_tree)
    assert (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json").exists()


def test_save_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    gzipped = _gzipped_repr(raw_tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    inv_store = InventoryStore(tmp_path)
    inv_store.save_inventory_tree(
        host_name=host_name,
        tree=deserialize_tree(raw_tree),
        meta=make_meta(do_archive=True),
    )
    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()


def test_remove_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    gzipped_repr = _gzipped_repr(raw_tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped_repr)
    gzipped_json = _gzipped_json(raw_tree)
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json", json.dumps(raw_tree)
    )
    cmk.ccc.store.save_bytes_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json.gz", gzipped_json
    )

    inv_store = InventoryStore(tmp_path)
    inv_store.remove_inventory_tree(host_name=host_name)
    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()


def test_load_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", raw_tree)

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_status_data_tree(host_name=host_name) == deserialize_tree(raw_tree)
    assert (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()


def test_save_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", raw_tree)

    inv_store = InventoryStore(tmp_path)
    inv_store.save_status_data_tree(host_name=host_name, tree=deserialize_tree(raw_tree))
    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.gz").exists()
    assert (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json.gz").exists()


def test_remove_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", raw_tree)
    cmk.ccc.store.save_text_to_file(
        tmp_path / "tmp/check_mk/status_data/hostname.json", json.dumps(raw_tree)
    )

    inv_store = InventoryStore(tmp_path)
    inv_store.remove_status_data_tree(host_name=host_name)
    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.gz").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json.gz").exists()


def test_load_previous_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", raw_tree
    )

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_previous_inventory_tree(host_name=host_name) == deserialize_tree(raw_tree)
    assert (tmp_path / "var/check_mk/inventory_archive/hostname/123").exists()
    assert not (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists()


def test_archive_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    raw_tree = _raw_tree("val")
    gzipped = _gzipped_repr(raw_tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    inv_store = InventoryStore(tmp_path)
    inv_store.archive_inventory_tree(host_name=host_name)
    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()

    archive_file_paths = list((tmp_path / "var/check_mk/inventory_archive/hostname").iterdir())
    assert archive_file_paths
    for archive_file_path in archive_file_paths:
        assert archive_file_path.suffixes == [".json"]


def test_load_history(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    for idx in range(5):
        raw_tree = _raw_tree(f"val-{idx}")
        cmk.ccc.store.save_object_to_file(
            tmp_path / f"var/check_mk/inventory_archive/hostname/{idx}", raw_tree
        )
    raw_tree = _raw_tree("val")
    gzipped = _gzipped_repr(raw_tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", raw_tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    inv_store = InventoryStore(tmp_path)
    history = load_history(
        inv_store,
        host_name,
        filter_history_paths=lambda ps: ps,
        filter_tree=None,
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
