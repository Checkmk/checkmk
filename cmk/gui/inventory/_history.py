#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    HistoryPath,
    ImmutableDeltaTree,
    ImmutableTree,
    load_delta_cache,
    load_tree,
    save_delta_cache,
    SDFilterChoice,
    TreeOrArchiveStore,
)

from cmk.gui.i18n import _

from ._tree import get_permitted_inventory_paths, make_filter_choices_from_permitted_paths


@dataclass(frozen=True)
class HistoryEntry:
    timestamp: int | None
    new: int
    changed: int
    removed: int
    delta_tree: ImmutableDeltaTree


def load_latest_delta_tree(hostname: HostName) -> ImmutableDeltaTree:
    filter_tree = (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := get_permitted_inventory_paths(), list)
        else None
    )
    history, _corrupted = _get_history(
        hostname,
        filter_history_paths=lambda pairs: [pairs[-1]] if pairs else [],
        filter_tree=filter_tree,
    )
    return history[0].delta_tree if history else ImmutableDeltaTree()


def _sort_corrupted_history_files(corrupted_history_files: Sequence[Path]) -> Sequence[str]:
    return sorted(
        [str(fp.relative_to(cmk.utils.paths.omd_root)) for fp in set(corrupted_history_files)]
    )


def load_delta_tree(
    hostname: HostName,
    timestamp: int,
) -> tuple[ImmutableDeltaTree, Sequence[str]]:
    """Load inventory history and compute delta tree of a specific timestamp"""
    # Timestamp is timestamp of the younger of both trees. For the oldest
    # tree we will just return the complete tree - without any delta
    # computation.

    def _search_timestamps(
        pairs: Sequence[tuple[HistoryPath, HistoryPath]], timestamp: int
    ) -> Sequence[tuple[HistoryPath, HistoryPath]]:
        for previous, current in pairs:
            if current.timestamp == timestamp:
                return [(previous, current)]
        raise MKGeneralException(
            _("Found no history entry at the time of '%s' for the host '%s'")
            % (timestamp, hostname)
        )

    filter_tree = (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := get_permitted_inventory_paths(), list)
        else None
    )
    history, corrupted = _get_history(
        hostname,
        filter_history_paths=lambda pairs: _search_timestamps(pairs, timestamp),
        filter_tree=filter_tree,
    )
    return (
        (history[0].delta_tree, _sort_corrupted_history_files(corrupted))
        if history
        else (ImmutableDeltaTree(), [])
    )


def get_history(hostname: HostName) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    filter_tree = (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := get_permitted_inventory_paths(), list)
        else None
    )
    history, corrupted = _get_history(
        hostname,
        filter_history_paths=lambda pairs: pairs,
        filter_tree=filter_tree,
    )
    return history, _sort_corrupted_history_files(corrupted)


def _get_pairs(
    history_file_paths: Sequence[HistoryPath],
) -> Sequence[tuple[HistoryPath, HistoryPath]]:
    if not history_file_paths:
        return []
    paths = [HistoryPath(Path(), None)] + list(history_file_paths)
    return list(zip(paths, paths[1:]))


def _get_history(
    hostname: HostName,
    *,
    filter_history_paths: Callable[
        [Sequence[tuple[HistoryPath, HistoryPath]]], Sequence[tuple[HistoryPath, HistoryPath]]
    ],
    filter_tree: Sequence[SDFilterChoice] | None,
) -> tuple[Sequence[HistoryEntry], Sequence[Path]]:
    if "/" in hostname:
        return [], []  # just for security reasons

    history_files = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    ).history(host_name=hostname)

    cached_tree_loader = _CachedTreeLoader()
    history: list[HistoryEntry] = []

    corrupted_deltas = []
    for previous, current in filter_history_paths(_get_pairs(history_files.paths)):
        if current.timestamp is None:
            continue

        cached_delta_tree_loader = _CachedDeltaTreeLoader(
            hostname,
            previous.timestamp,
            current.timestamp,
        )

        if (
            cached_history_entry := cached_delta_tree_loader.get_cached_entry(filter_tree)
        ) is not None:
            history.append(cached_history_entry)
            continue

        try:
            previous_tree = cached_tree_loader.get_tree(previous.path)
        except FileNotFoundError:
            corrupted_deltas.append(previous.path)
            continue

        try:
            current_tree = cached_tree_loader.get_tree(current.path)
        except FileNotFoundError:
            corrupted_deltas.append(current.path)
            continue

        if (
            history_entry := cached_delta_tree_loader.get_calculated_or_store_entry(
                previous_tree, current_tree, filter_tree
            )
        ) is not None:
            history.append(history_entry)

    return history, list(history_files.corrupted) + corrupted_deltas


@dataclass(frozen=True)
class _CachedTreeLoader:
    _lookup: dict[Path, ImmutableTree] = field(default_factory=dict)

    def get_tree(self, filepath: Path) -> ImmutableTree:
        if filepath == Path():
            return ImmutableTree()

        if filepath in self._lookup:
            return self._lookup[filepath]

        return self._lookup.setdefault(filepath, load_tree(filepath))


@dataclass(frozen=True)
class _CachedDeltaTreeLoader:
    hostname: HostName
    previous_timestamp: int | None
    current_timestamp: int

    @property
    def path(self) -> Path:
        return Path(
            cmk.utils.paths.inventory_delta_cache_dir,
            self.hostname,
            f"{self.previous_timestamp}_{self.current_timestamp}",
        )

    def get_cached_entry(self, filter_tree: Sequence[SDFilterChoice] | None) -> HistoryEntry | None:
        try:
            cached_data = load_delta_cache(self.path)
        except MKGeneralException:
            return None

        if cached_data is None:
            return None

        new, changed, removed, delta_tree = cached_data
        return self._make_history_entry(new, changed, removed, delta_tree, filter_tree)

    def get_calculated_or_store_entry(
        self,
        previous_tree: ImmutableTree,
        current_tree: ImmutableTree,
        filter_tree: Sequence[SDFilterChoice] | None,
    ) -> HistoryEntry | None:
        delta_tree = current_tree.difference(previous_tree)
        delta_stats = delta_tree.get_stats()
        new = delta_stats["new"]
        changed = delta_stats["changed"]
        removed = delta_stats["removed"]
        if new or changed or removed:
            save_delta_cache(self.path, (new, changed, removed, delta_tree))
            return self._make_history_entry(new, changed, removed, delta_tree, filter_tree)
        return None

    def _make_history_entry(
        self,
        new: int,
        changed: int,
        removed: int,
        delta_tree: ImmutableDeltaTree,
        filter_tree: Sequence[SDFilterChoice] | None,
    ) -> HistoryEntry | None:
        if filter_tree is None:
            return HistoryEntry(self.current_timestamp, new, changed, removed, delta_tree)

        if not (filtered_delta_tree := delta_tree.filter(filter_tree)):
            return None

        delta_stats = filtered_delta_tree.get_stats()
        return HistoryEntry(
            self.current_timestamp,
            delta_stats["new"],
            delta_stats["changed"],
            delta_stats["removed"],
            filtered_delta_tree,
        )
