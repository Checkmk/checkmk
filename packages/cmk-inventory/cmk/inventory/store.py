#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import io
import json
import os
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName

from .merging import merge_trees
from .paths import InventoryPaths, parse_archive_timestamp, tree_mtime, TreePath, TreePathGz
from .serialization import (
    deserialize_tree,
    make_meta,
    parse_from_raw_status_data_tree,
    SDMeta,
    SDMetaAndRawTree,
    SDRawTree,
    serialize_tree,
)
from .trees import ImmutableTree, MutableTree, SDPath


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


def load_tree_from_tree_path(tree_path: TreePath, *, debug: bool) -> ImmutableTree:
    if raw_tree := store.load_text_from_file_explicit(tree_path.path, debug=debug):
        return deserialize_tree(json.loads(raw_tree))
    if raw_tree := store.load_object_from_file_explicit(
        tree_path.legacy, default=None, debug=debug
    ):
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


def _archive_inventory_tree(inv_paths: InventoryPaths, host_name: HostName, *, debug: bool) -> None:
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

    if raw_tree := store.load_object_from_file_explicit(
        tree_path.legacy, default=None, debug=debug
    ):
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
        _archive_inventory_tree(self.inv_paths, host_name, debug=debug)


def _render_update_results(update_results: Mapping[SDPath, Sequence[str]]) -> str:
    lines = ["Updated inventory tree:"]
    for path, messages in update_results.items():
        lines.append(f"  Path '{' > '.join(path)}':")
        lines.extend(f"    {r}" for r in sorted(messages))
    return "\n".join(lines)


@dataclass(frozen=True, kw_only=True)
class _SaveTreeActions:
    do_archive: bool
    do_save: bool
    messages: Sequence[str]


def _get_save_tree_actions(
    *, previous_tree: ImmutableTree, inventory_tree: MutableTree
) -> _SaveTreeActions:
    if not inventory_tree:
        return _SaveTreeActions(do_archive=True, do_save=False, messages=["No inventory tree."])

    if not previous_tree:
        return _SaveTreeActions(do_archive=False, do_save=True, messages=["New inventory tree."])

    messages = []
    if has_changed := previous_tree != inventory_tree:
        messages.append("Inventory tree has changed.")

    if update_results := inventory_tree.get_update_results():
        messages.append(_render_update_results(update_results))

    return _SaveTreeActions(
        do_archive=has_changed,
        do_save=(has_changed or len(update_results) > 0),
        messages=messages,
    )


class InventoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def load_inventory_tree(self, *, host_name: HostName) -> ImmutableTree:
        return load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name), debug=False)

    def save_inventory_tree(
        self, *, host_name: HostName, tree: MutableTree | ImmutableTree, meta: SDMeta
    ) -> None:
        raw_tree = serialize_tree(tree)

        tree_path = self.inv_paths.inventory_tree(host_name)
        save_raw_tree(tree_path, raw_tree)
        tree_path.legacy.unlink(missing_ok=True)

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        save_raw_tree_gz(tree_path_gz, SDMetaAndRawTree(meta=meta, raw_tree=raw_tree))
        tree_path_gz.legacy.unlink(missing_ok=True)

        self.inv_paths.inventory_marker_file.touch()

    def remove_inventory_tree(self, *, host_name: HostName) -> None:
        tree_path = self.inv_paths.inventory_tree(host_name)
        tree_path.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        tree_path_gz.path.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)

    def load_status_data_tree(self, *, host_name: HostName) -> ImmutableTree:
        return load_tree_from_tree_path(self.inv_paths.status_data_tree(host_name), debug=False)

    def save_status_data_tree(
        self, *, host_name: HostName, tree: MutableTree | ImmutableTree
    ) -> None:
        tree_path = self.inv_paths.status_data_tree(host_name)
        save_raw_tree(tree_path, serialize_tree(tree))
        tree_path.legacy.unlink(missing_ok=True)

        self.inv_paths.status_data_marker_file.touch()

    def remove_status_data_tree(self, *, host_name: HostName) -> None:
        tree_path = self.inv_paths.status_data_tree(host_name)
        tree_path.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)

    def load_merged_tree(
        self, *, host_name: HostName, raw_status_data_tree: bytes
    ) -> ImmutableTree:
        return merge_trees(
            self.load_inventory_tree(host_name=host_name),
            (
                parse_from_raw_status_data_tree(raw_status_data_tree)
                if raw_status_data_tree
                else self.load_status_data_tree(host_name=host_name)
            ),
        )

    def load_previous_inventory_tree(self, *, host_name: HostName, debug: bool) -> ImmutableTree:
        if tree := load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name), debug=debug):
            return tree

        try:
            latest_archive_file_path = max(
                self.inv_paths.archive_host(host_name).iterdir(),
                key=parse_archive_timestamp,
            )
        except FileNotFoundError, ValueError:
            return ImmutableTree()

        return load_tree_from_tree_path(
            TreePath.from_archive_or_delta_cache_file_path(latest_archive_file_path), debug=debug
        )

    def archive_inventory_tree(self, *, host_name: HostName, debug: bool) -> None:
        _archive_inventory_tree(self.inv_paths, host_name, debug=debug)

    def save_if_changed(
        self,
        *,
        host_name: HostName,
        previous_tree: ImmutableTree,
        tree: MutableTree,
        debug: bool,
    ) -> Sequence[str]:
        actions = _get_save_tree_actions(previous_tree=previous_tree, inventory_tree=tree)
        messages = list(actions.messages)
        if actions.do_archive:
            messages.append("Archive current inventory tree.")
            self.archive_inventory_tree(host_name=host_name, debug=debug)
        if actions.do_save:
            messages.append("Save new inventory tree.")
            self.save_inventory_tree(
                host_name=host_name,
                tree=tree,
                meta=make_meta(do_archive=actions.do_archive),
            )
        return messages
