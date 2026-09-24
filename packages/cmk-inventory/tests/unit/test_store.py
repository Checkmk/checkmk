#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import json
import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.serialization import (
    deserialize_tree,
    SDRawTree,
    serialize_tree,
)
from cmk.inventory.store import (
    InventoryStore,
    make_meta,
    parse_from_gzipped,
    parse_from_raw_status_data_tree,
    RawInventoryStore,
    rename,
    SDMeta,
    SDMetaAndRawTree,
)
from cmk.inventory.trees import MutableTree, SDKey, SDNodeName

from ._fixtures import gzipped_json, gzipped_repr, inventory_store, raw_tree


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


@pytest.mark.parametrize(
    "do_archive",
    [
        pytest.param(True, id="do-archive"),
        pytest.param(False, id="do-not-archive"),
    ],
)
def test_save_inventory_tree_writes_the_meta(tmp_path: Path, do_archive: bool) -> None:
    host_name = HostName("heute")
    tree = MutableTree()
    tree.add(
        path=(SDNodeName("path-to"), SDNodeName("node")), pairs=[{SDKey("foo"): 1, SDKey("bär"): 2}]
    )
    inv_store = InventoryStore(tmp_path)
    inv_store.save_inventory_tree(
        host_name=host_name,
        tree=tree,
        meta=make_meta(do_archive=do_archive),
    )

    assert (tmp_path / "var/check_mk/inventory/heute.json").exists()
    assert not (tmp_path / "var/check_mk/inventory/heute").exists()
    assert (tmp_path / "var/check_mk/inventory/heute.json.gz").exists()
    assert not (tmp_path / "var/check_mk/inventory/heute.gz").exists()

    with (tmp_path / "var/check_mk/inventory/heute.json.gz").open("rb") as f:
        content = f.read()

    meta_and_raw_tree = parse_from_gzipped(content)
    assert meta_and_raw_tree["meta"]["version"] == "1"
    assert meta_and_raw_tree["meta"]["do_archive"] is do_archive

    expected_raw_tree = serialize_tree(tree)
    assert meta_and_raw_tree["raw_tree"]["Attributes"] == expected_raw_tree["Attributes"]
    assert meta_and_raw_tree["raw_tree"]["Table"] == expected_raw_tree["Table"]
    assert meta_and_raw_tree["raw_tree"]["Nodes"] == expected_raw_tree["Nodes"]


@pytest.mark.parametrize(
    "raw, expected",
    [
        pytest.param(
            {"Attributes": {}, "Table": {}, "Nodes": {}},
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="missing-version:missing-meta",
        ),
        pytest.param(
            {
                "meta_version": "0",
                "meta_do_archive": True,
                "Attributes": {},
                "Table": {},
                "Nodes": {},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=0:do-archive",
        ),
        pytest.param(
            {
                "meta_version": "0",
                "meta_do_archive": False,
                "Attributes": {},
                "Table": {},
                "Nodes": {},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=False),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=0:do-not-archive",
        ),
        pytest.param(
            {
                "meta": {"version": "1", "do_archive": True},
                "raw_tree": {"Attributes": {}, "Table": {}, "Nodes": {}},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=True),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=1:do-archive",
        ),
        pytest.param(
            {
                "meta": {"version": "1", "do_archive": False},
                "raw_tree": {"Attributes": {}, "Table": {}, "Nodes": {}},
            },
            SDMetaAndRawTree(
                meta=SDMeta(version="1", do_archive=False),
                raw_tree=SDRawTree(Attributes={}, Table={}, Nodes={}),
            ),
            id="version=1:do-archive",
        ),
    ],
)
def test_parse_from_gzipped(raw: Mapping[str, object], expected: SDMetaAndRawTree) -> None:
    assert parse_from_gzipped(gzip.compress(json.dumps(raw).encode())) == expected


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


def test_parse_from_raw_status_data_tree() -> None:
    tree = raw_tree("val")
    assert parse_from_raw_status_data_tree(json.dumps(tree).encode()) == deserialize_tree(tree)


def test_parse_from_raw_status_data_tree_legacy() -> None:
    tree = raw_tree("val")
    assert parse_from_raw_status_data_tree(repr(tree).encode()) == deserialize_tree(tree)


@pytest.mark.parametrize(
    "tree_name",
    [
        HostName("tree_addresses_ordered"),
        HostName("tree_addresses_unordered"),
        HostName("tree_inv"),
        HostName("tree_new_addresses"),
        HostName("tree_new_addresses_arrays_memory"),
        HostName("tree_new_arrays"),
        HostName("tree_new_heute"),
        HostName("tree_new_interfaces"),
        HostName("tree_new_large_ora_tablespaces_fixed_len"),
        HostName("tree_new_large_ora_tablespaces_variable_len"),
        HostName("tree_new_memory"),
        HostName("tree_old_addresses"),
        HostName("tree_old_addresses_arrays_memory"),
        HostName("tree_old_arrays"),
        HostName("tree_old_heute"),
        HostName("tree_old_interfaces"),
        HostName("tree_old_large_ora_tablespaces"),
        HostName("tree_old_memory"),
        HostName("tree_status"),
    ],
)
def test_load_from(tree_name: HostName) -> None:
    inventory_store().load_inventory_tree(host_name=tree_name)


@pytest.mark.parametrize(
    "tree_name",
    [
        HostName("tree_old_addresses_arrays_memory"),
        HostName("tree_old_addresses"),
        HostName("tree_old_arrays"),
        HostName("tree_old_interfaces"),
        HostName("tree_old_memory"),
        HostName("tree_old_heute"),
        HostName("tree_new_addresses_arrays_memory"),
        HostName("tree_new_addresses"),
        HostName("tree_new_arrays"),
        HostName("tree_new_interfaces"),
        HostName("tree_new_memory"),
        HostName("tree_new_heute"),
    ],
)
def test_save_and_load_real_tree(tree_name: HostName, tmp_path: Path) -> None:
    orig_tree = inventory_store().load_inventory_tree(host_name=tree_name)
    inv_store = InventoryStore(tmp_path)
    try:
        inv_store.save_inventory_tree(
            host_name=HostName("foo"),
            tree=orig_tree,
            meta=make_meta(do_archive=False),
        )
        loaded_tree = inv_store.load_inventory_tree(host_name=HostName("foo"))
        assert orig_tree == loaded_tree
    finally:
        shutil.rmtree(str(tmp_path))
