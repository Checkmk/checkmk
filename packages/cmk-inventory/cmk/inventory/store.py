#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName

from .filtering import filter_tree, SDFilterChoice
from .merging import merge_trees
from .paths import InventoryPaths, parse_archive_timestamp, TreePath
from .raw_store import (
    archive_inventory_tree,
    load_tree_from_tree_path,
    save_raw_tree,
    save_raw_tree_gz,
)
from .serialization import (
    make_meta,
    parse_from_raw_status_data_tree,
    SDMeta,
    SDMetaAndRawTree,
    serialize_tree,
)
from .trees import ImmutableTree, MutableTree, SDPath


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
        return load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name))

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
        return load_tree_from_tree_path(self.inv_paths.status_data_tree(host_name))

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
        self,
        *,
        host_name: HostName,
        raw_status_data_tree: bytes,
        tree_filters: Sequence[SDFilterChoice] | None,
    ) -> ImmutableTree:
        merged_tree = merge_trees(
            self.load_inventory_tree(host_name=host_name),
            (
                parse_from_raw_status_data_tree(raw_status_data_tree)
                if raw_status_data_tree
                else self.load_status_data_tree(host_name=host_name)
            ),
        )
        return merged_tree if tree_filters is None else filter_tree(merged_tree, tree_filters)

    def load_previous_inventory_tree(self, *, host_name: HostName) -> ImmutableTree:
        if tree := load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name)):
            return tree

        try:
            latest_archive_file_path = max(
                self.inv_paths.archive_host(host_name).iterdir(),
                key=parse_archive_timestamp,
            )
        except FileNotFoundError, ValueError:
            return ImmutableTree()

        return load_tree_from_tree_path(
            TreePath.from_archive_or_delta_cache_file_path(latest_archive_file_path)
        )

    def save_if_changed(
        self,
        *,
        host_name: HostName,
        previous_tree: ImmutableTree,
        tree: MutableTree,
    ) -> Sequence[str]:
        actions = _get_save_tree_actions(previous_tree=previous_tree, inventory_tree=tree)
        messages = list(actions.messages)
        if actions.do_archive:
            messages.append("Archive current inventory tree.")
            archive_inventory_tree(self.inv_paths, host_name, debug=False)
        if actions.do_save:
            messages.append("Save new inventory tree.")
            self.save_inventory_tree(
                host_name=host_name,
                tree=tree,
                meta=make_meta(do_archive=actions.do_archive),
            )
        return messages
