#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
import json
import os
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName

from .paths import InventoryPaths, tree_mtime, TreePath, TreePathGz
from .serialization import deserialize_tree, SDMetaAndRawTree, SDRawTree
from .trees import ImmutableTree


def rename(
    omd_root: Path, *, old_host_name: HostName, new_host_name: HostName
) -> Sequence[Literal["inv", "invarch"]]:
    inv_paths = InventoryPaths(omd_root)
    actions: set[Literal["inv", "invarch"]] = set()
    for old_file_path, new_file_path in zip(
        inv_paths.host_tree_files(HostName(old_host_name)),
        inv_paths.host_tree_files(HostName(new_host_name)),
        strict=True,
    ):
        try:
            old_file_path.rename(new_file_path)
            actions.add("inv")
        except FileNotFoundError:
            pass

    for old_directory, new_directory in [
        (
            inv_paths.archive_host(HostName(old_host_name)),
            inv_paths.archive_host(HostName(new_host_name)),
        ),
        (
            inv_paths.delta_cache_host(HostName(old_host_name)),
            inv_paths.delta_cache_host(HostName(new_host_name)),
        ),
    ]:
        try:
            shutil.move(old_directory, new_directory)
            actions.add("invarch")
        except FileNotFoundError:
            pass

    return list(actions)


def load_tree_from_tree_path(tree_path: TreePath) -> ImmutableTree:
    if raw_tree := store.load_text_from_file(tree_path.path, debug=False):
        return deserialize_tree(json.loads(raw_tree))
    if raw_tree := store.load_object_from_file(tree_path.legacy, default=None, debug=False):
        return deserialize_tree(raw_tree)
    return ImmutableTree()


def save_raw_tree(tree_path: TreePath, raw_tree: SDRawTree) -> None:
    tree_path.path.parent.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(tree_path.path, json.dumps(raw_tree) + "\n")


def save_raw_tree_gz(tree_path_gz: TreePathGz, meta_and_raw_tree: SDMetaAndRawTree) -> None:
    tree_path_gz.path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write((json.dumps(meta_and_raw_tree) + "\n").encode("utf-8"))
    store.save_bytes_to_file(tree_path_gz.path, buf.getvalue())


def archive_inventory_tree(inv_paths: InventoryPaths, host_name: HostName, *, debug: bool) -> None:
    tree_path = inv_paths.inventory_tree(host_name)
    if (mtime := tree_mtime(tree_path)) is None:
        return

    tree_path_gz = inv_paths.inventory_tree_gz(host_name)
    archive_tree = inv_paths.archive_tree(host_name, mtime)

    if tree_path.path.exists():
        inv_paths.archive_host(host_name).mkdir(parents=True, exist_ok=True)
        tree_path.path.rename(archive_tree.path)
        tree_path_gz.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)
        return

    if raw_tree := store.load_object_from_file(tree_path.legacy, default=None, debug=debug):
        inv_paths.archive_host(host_name).mkdir(parents=True, exist_ok=True)
        store.save_text_to_file(archive_tree.path, json.dumps(raw_tree))
        tree_path.legacy.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)


class RawInventoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def save_meta_and_raw_inventory_tree(
        self, *, host_name: HostName, meta_and_raw_tree: SDMetaAndRawTree, timestamp: int
    ) -> None:
        tree_path = self.inv_paths.inventory_tree(host_name)
        save_raw_tree(tree_path, meta_and_raw_tree["raw_tree"])
        tree_path.legacy.unlink(missing_ok=True)
        os.utime(tree_path.path, (timestamp, timestamp))

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        save_raw_tree_gz(tree_path_gz, meta_and_raw_tree)
        tree_path_gz.legacy.unlink(missing_ok=True)
        os.utime(tree_path_gz.path, (timestamp, timestamp))

    def archive_inventory_tree(self, *, host_name: HostName, debug: bool) -> None:
        archive_inventory_tree(self.inv_paths, host_name, debug=debug)
