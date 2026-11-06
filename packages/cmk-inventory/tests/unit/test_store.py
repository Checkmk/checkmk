#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.config import RawIntervalFromConfig
from cmk.inventory.filtering import SDFilterChoice
from cmk.inventory.paths import has_archive, InventoryPaths
from cmk.inventory.retention import update_from_previous
from cmk.inventory.serialization import (
    deserialize_tree,
    make_meta,
    parse_from_gzipped,
    SDMeta,
    SDMetaAndRawTree,
    SDRawTree,
    serialize_tree,
)
from cmk.inventory.store import InventoryStore
from cmk.inventory.trees import (
    ImmutableAttributes,
    ImmutableTree,
    MutableTree,
    SDKey,
    SDNodeName,
)

from ._fixtures import gzipped_json, gzipped_repr, inventory_store, raw_tree


def test_load_inventory_tree_legacy(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "var/check_mk/inventory/hostname", tree)

    assert (
        InventoryStore(tmp_path).load_inventory_tree(host_name=host_name),
        (tmp_path / "var/check_mk/inventory/hostname").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.json").exists(),
    ) == (deserialize_tree(tree), True, False)


def test_load_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json", json.dumps(tree)
    )

    assert (
        InventoryStore(tmp_path).load_inventory_tree(host_name=host_name),
        (tmp_path / "var/check_mk/inventory/hostname").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.json").exists(),
    ) == (deserialize_tree(tree), False, True)


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
    assert (
        (tmp_path / "var/check_mk/inventory/hostname").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.gz").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.json").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists(),
    ) == (False, False, True, True)


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
    assert (
        (tmp_path / "var/check_mk/inventory/hostname").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.gz").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.json").exists(),
        (tmp_path / "var/check_mk/inventory/hostname.json.gz").exists(),
    ) == (False, False, False, False)


def test_load_status_data_tree_legacy(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)

    assert (
        InventoryStore(tmp_path).load_status_data_tree(host_name=host_name),
        (tmp_path / "tmp/check_mk/status_data/hostname").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.json").exists(),
    ) == (deserialize_tree(tree), True, False)


def test_load_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_text_to_file(
        tmp_path / "tmp/check_mk/status_data/hostname.json", json.dumps(tree)
    )

    assert (
        InventoryStore(tmp_path).load_status_data_tree(host_name=host_name),
        (tmp_path / "tmp/check_mk/status_data/hostname").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.json").exists(),
    ) == (deserialize_tree(tree), False, True)


def test_save_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)

    inv_store = InventoryStore(tmp_path)
    inv_store.save_status_data_tree(host_name=host_name, tree=deserialize_tree(tree))
    assert (
        (tmp_path / "tmp/check_mk/status_data/hostname").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.gz").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.json").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.json.gz").exists(),
    ) == (False, False, True, False)


def test_remove_status_data_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(tmp_path / "tmp/check_mk/status_data/hostname", tree)
    cmk.ccc.store.save_text_to_file(
        tmp_path / "tmp/check_mk/status_data/hostname.json", json.dumps(tree)
    )

    inv_store = InventoryStore(tmp_path)
    inv_store.remove_status_data_tree(host_name=host_name)
    assert (
        (tmp_path / "tmp/check_mk/status_data/hostname").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.gz").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.json").exists(),
        (tmp_path / "tmp/check_mk/status_data/hostname.json.gz").exists(),
    ) == (False, False, False, False)


def test_load_previous_inventory_tree(tmp_path: Path) -> None:
    host_name = HostName("hostname")
    tree = raw_tree("val")
    cmk.ccc.store.save_object_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123", tree
    )

    assert (
        InventoryStore(tmp_path).load_previous_inventory_tree(host_name=host_name),
        (tmp_path / "var/check_mk/inventory_archive/hostname/123").exists(),
        (tmp_path / "var/check_mk/inventory_archive/hostname/123.json").exists(),
    ) == (deserialize_tree(tree), True, False)


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

    assert (
        parse_from_gzipped((tmp_path / "var/check_mk/inventory/heute.json.gz").read_bytes()),
        (tmp_path / "var/check_mk/inventory/heute.json").exists(),
        (tmp_path / "var/check_mk/inventory/heute").exists(),
        (tmp_path / "var/check_mk/inventory/heute.gz").exists(),
    ) == (
        SDMetaAndRawTree(
            meta=SDMeta(version="1", do_archive=do_archive), raw_tree=serialize_tree(tree)
        ),
        True,
        False,
        False,
    )


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
def test_load_real_tree_files_without_an_error(tree_name: HostName) -> None:
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
    inv_store.save_inventory_tree(
        host_name=HostName("foo"),
        tree=orig_tree,
        meta=make_meta(do_archive=False),
    )
    assert inv_store.load_inventory_tree(host_name=HostName("foo")) == orig_tree


def test_load_previous_inventory_tree_prefers_the_current_tree(tmp_path: Path) -> None:
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory/hostname.json", json.dumps(raw_tree("current"))
    )
    cmk.ccc.store.save_text_to_file(
        tmp_path / "var/check_mk/inventory_archive/hostname/123.json",
        json.dumps(raw_tree("archived")),
    )

    tree = InventoryStore(tmp_path).load_previous_inventory_tree(host_name=HostName("hostname"))

    assert tree == deserialize_tree(raw_tree("current"))


def test_load_previous_inventory_tree_without_any_tree_is_empty(tmp_path: Path) -> None:
    assert not InventoryStore(tmp_path).load_previous_inventory_tree(host_name=HostName("hostname"))


def _tree_with(key: str, value: str) -> SDRawTree:
    return SDRawTree(Attributes={"Pairs": {SDKey(key): value}}, Table={}, Nodes={})


def _save_inventory_and_status_data_trees(store: InventoryStore, host_name: HostName) -> None:
    store.save_inventory_tree(
        host_name=host_name,
        tree=deserialize_tree(_tree_with("inv", "1")),
        meta=make_meta(do_archive=False),
    )
    store.save_status_data_tree(host_name=host_name, tree=deserialize_tree(_tree_with("file", "2")))


def test_load_merged_tree_merges_the_status_data_file(tmp_path: Path) -> None:
    store = InventoryStore(tmp_path)
    _save_inventory_and_status_data_trees(store, HostName("hostname"))

    assert store.load_merged_tree(
        host_name=HostName("hostname"), raw_status_data_tree=b"", tree_filters=None
    ) == deserialize_tree(
        SDRawTree(Attributes={"Pairs": {SDKey("inv"): "1", SDKey("file"): "2"}}, Table={}, Nodes={})
    )


def test_load_merged_tree_prefers_the_raw_status_data_to_the_file(tmp_path: Path) -> None:
    store = InventoryStore(tmp_path)
    _save_inventory_and_status_data_trees(store, HostName("hostname"))

    assert store.load_merged_tree(
        host_name=HostName("hostname"),
        raw_status_data_tree=json.dumps(_tree_with("raw", "3")).encode(),
        tree_filters=None,
    ) == deserialize_tree(
        SDRawTree(Attributes={"Pairs": {SDKey("inv"): "1", SDKey("raw"): "3"}}, Table={}, Nodes={})
    )


def test_load_merged_tree_keeps_only_the_filtered_keys(tmp_path: Path) -> None:
    store = InventoryStore(tmp_path)
    _save_inventory_and_status_data_trees(store, HostName("hostname"))

    assert store.load_merged_tree(
        host_name=HostName("hostname"),
        raw_status_data_tree=b"",
        tree_filters=[
            SDFilterChoice(path=(), pairs=[SDKey("file")], columns="nothing", nodes="nothing")
        ],
    ) == deserialize_tree(SDRawTree(Attributes={"Pairs": {SDKey("file"): "2"}}, Table={}, Nodes={}))


def _previous_tree(value: str) -> ImmutableTree:
    return ImmutableTree(attributes=ImmutableAttributes(pairs={SDKey("key"): value}))


def _current_tree(value: str) -> MutableTree:
    tree = MutableTree()
    tree.add(path=(), pairs=[{SDKey("key"): value}])
    return tree


def _retained_tree(value: str) -> MutableTree:
    tree = _current_tree(value)
    update_from_previous(
        tree,
        now=0,
        previous_tree=ImmutableTree(),
        raw_intervals_from_config=[
            RawIntervalFromConfig(interval=30, visible_raw_path="", attributes="all")
        ],
        pairs_cache_info={(): (10, 20)},
        columns_cache_info={},
    )
    return tree


def _save_if_changed(
    tmp_path: Path, previous_tree: ImmutableTree, tree: MutableTree
) -> Sequence[str]:
    store = InventoryStore(tmp_path)
    if previous_tree:
        store.save_inventory_tree(
            host_name=HostName("host"), tree=previous_tree, meta=make_meta(do_archive=False)
        )
        store.inv_paths.inventory_marker_file.unlink()
    return store.save_if_changed(host_name=HostName("host"), previous_tree=previous_tree, tree=tree)


@pytest.mark.parametrize(
    "previous_tree, tree, archived_and_saved",
    [
        pytest.param(_previous_tree("old"), MutableTree(), (True, False), id="no-tree"),
        pytest.param(ImmutableTree(), _current_tree("new"), (False, True), id="new-tree"),
        pytest.param(_previous_tree("old"), _current_tree("new"), (True, True), id="changed"),
        pytest.param(_previous_tree("same"), _current_tree("same"), (False, False), id="unchanged"),
        pytest.param(
            _previous_tree("same"),
            _retained_tree("same"),
            (False, True),
            id="unchanged-with-update-results",
        ),
    ],
)
def test_save_if_changed(
    tmp_path: Path,
    previous_tree: ImmutableTree,
    tree: MutableTree,
    archived_and_saved: tuple[bool, bool],
) -> None:
    _save_if_changed(tmp_path, previous_tree, tree)
    inv_paths = InventoryPaths(tmp_path)
    assert (
        has_archive(inv_paths, HostName("host")),
        inv_paths.inventory_marker_file.exists(),
    ) == archived_and_saved


def test_save_if_changed_reports_the_update_results(tmp_path: Path) -> None:
    assert _save_if_changed(tmp_path, _previous_tree("same"), _retained_tree("same")) == [
        "Updated inventory tree:\n  Path '':\n    [Attributes] Keep until: key (60)",
        "Save new inventory tree.",
    ]
