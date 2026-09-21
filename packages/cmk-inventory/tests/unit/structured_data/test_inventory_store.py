#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.structured_data import (
    deserialize_delta_tree,
    deserialize_tree,
    InventoryStore,
    make_meta,
    rename,
    SDKey,
    SDRawDeltaTree,
)

from .._fixtures import gzipped_json, gzipped_repr, raw_tree


def test_load_inventory_tree_legacy(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_inventory_tree(host_name=host_name) == deserialize_tree(tree)
    assert (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json").exists()


def test_load_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json", json.dumps(tree)
    )

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_inventory_tree(host_name=host_name) == deserialize_tree(tree)
    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()


def test_save_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    gzipped = gzipped_repr(tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)
    cmk.ccc.store.save_bytes_to_file(tmp_path / "var/check_mk/inventory/hostname.gz", gzipped)

    inv_store = InventoryStore(tmp_path)
    inv_store.save_inventory_tree(
        host_name=host_name,
        tree=deserialize_tree(tree),
        meta=make_meta(do_archive=True),
    )
    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()


def test_remove_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    gzipped_as_repr = gzipped_repr(tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)
    cmk.ccc.store.save_bytes_to_file(
        tmp_path / "var/check_mk/inventory/hostname.gz", gzipped_as_repr
    )
    gzipped_as_json = gzipped_json(tree)
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json", json.dumps(tree)
    )
    cmk.ccc.store.save_bytes_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json.gz", gzipped_as_json
    )

    inv_store = InventoryStore(tmp_path)
    inv_store.remove_inventory_tree(host_name=host_name)
    assert not (tmp_path / "var/check_mk/inventory/hostname").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.gz").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json").exists()
    assert not (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists()


def test_load_status_data_tree_legacy(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_status_data_tree(host_name=host_name) == deserialize_tree(tree)
    assert (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()


def test_load_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_text_to_file(
        tmp_path / "tmp/check_mk/status_data/hostname.json", json.dumps(tree)
    )

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_status_data_tree(host_name=host_name) == deserialize_tree(tree)
    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()


def test_save_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)

    inv_store = InventoryStore(tmp_path)
    inv_store.save_status_data_tree(host_name=host_name, tree=deserialize_tree(tree))
    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.gz").exists()
    assert (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json.gz").exists()


def test_remove_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)
    cmk.ccc.store.save_text_to_file(
        tmp_path / "tmp/check_mk/status_data/hostname.json", json.dumps(tree)
    )

    inv_store = InventoryStore(tmp_path)
    inv_store.remove_status_data_tree(host_name=host_name)
    assert not (tmp_path / "tmp/check_mk/status_data/hostname").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.gz").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json").exists()
    assert not (tmp_path / "tmp/check_mk/status_data/hostname.json.gz").exists()


def test_load_previous_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", tree
    )

    inv_store = InventoryStore(tmp_path)
    assert inv_store.load_previous_inventory_tree(host_name=host_name) == deserialize_tree(tree)
    assert (tmp_path / "var/check_mk/inventory_archive/hostname/123").exists()
    assert not (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists()


def test_archive_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    gzipped = gzipped_repr(tree)
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)
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

    assert not (tmp_path / f"var/check_mk/inventory/{old_host_name}").exists()
    assert (tmp_path / f"var/check_mk/inventory/{new_host_name}").exists()
    assert not (tmp_path / f"var/check_mk/inventory/{old_host_name}.gz").exists()
    assert (tmp_path / f"var/check_mk/inventory/{new_host_name}.gz").exists()
    assert not (tmp_path / f"tmp/check_mk/status_data/{old_host_name}").exists()
    assert (tmp_path / f"tmp/check_mk/status_data/{new_host_name}").exists()

    assert not (tmp_path / f"var/check_mk/inventory_archive/{old_host_name}").exists()
    for idx in timestamps:
        assert not (tmp_path / f"var/check_mk/inventory_archive/{old_host_name}/{idx}").exists()
        assert (tmp_path / f"var/check_mk/inventory_archive/{new_host_name}/{idx}").exists()

    assert not (tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}").exists()
    for prev, cur in zip(timestamps, timestamps[1:]):
        assert not (
            tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}/{prev}_{cur}"
        ).exists()
        assert (
            tmp_path / f"var/check_mk/inventory_delta_cache/{new_host_name}/{prev}_{cur}"
        ).exists()


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

    assert not (tmp_path / f"var/check_mk/inventory/{old_host_name}.json").exists()
    assert (tmp_path / f"var/check_mk/inventory/{new_host_name}.json").exists()
    assert not (tmp_path / f"var/check_mk/inventory/{old_host_name}.json.gz").exists()
    assert (tmp_path / f"var/check_mk/inventory/{new_host_name}.json.gz").exists()
    assert not (tmp_path / f"tmp/check_mk/status_data/{old_host_name}.json").exists()
    assert (tmp_path / f"tmp/check_mk/status_data/{new_host_name}.json").exists()

    assert not (tmp_path / f"var/check_mk/inventory_archive/{old_host_name}").exists()
    for idx in timestamps:
        assert not (
            tmp_path / f"var/check_mk/inventory_archive/{old_host_name}/{idx}.json"
        ).exists()
        assert (tmp_path / f"var/check_mk/inventory_archive/{new_host_name}/{idx}.json").exists()

    assert not (tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}").exists()
    for prev, cur in zip(timestamps, timestamps[1:]):
        assert not (
            tmp_path / f"var/check_mk/inventory_delta_cache/{old_host_name}/{prev}_{cur}.json"
        ).exists()
        assert (
            tmp_path / f"var/check_mk/inventory_delta_cache/{new_host_name}/{prev}_{cur}.json"
        ).exists()


def test_deserialize_delta_tree_with_attributes_key() -> None:
    """Regression test for crash groups 3652/3629.

    The old ImmutableDeltaTree._deserialize class method accessed raw_tree["Attributes"]
    which raised KeyError when old cached delta tree files lacked that key.  That class
    method was removed in favour of the standalone deserialize_delta_tree() function which
    is the sole public entry point.  The current serialisation always produces an
    "Attributes" key, so roundtripping through serialize/deserialize must never raise
    KeyError.
    """
    raw_delta_tree = SDRawDeltaTree(
        Attributes={"Pairs": {SDKey("k"): (None, "v")}},
        Table={},
        Nodes={},
    )
    delta_tree = deserialize_delta_tree(raw_delta_tree)
    assert delta_tree.attributes.pairs[SDKey("k")].old is None
    assert delta_tree.attributes.pairs[SDKey("k")].new == "v"
