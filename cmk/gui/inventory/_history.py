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
    delta_history, _corrupted_history_files = _get_history(
        hostname,
        filter_history_paths=lambda pairs: [pairs[-1]] if pairs else [],
    )
    return delta_history[0].delta_tree if delta_history else ImmutableDeltaTree()


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

    delta_history, corrupted_history_files = _get_history(
        hostname,
        filter_history_paths=lambda pairs: _search_timestamps(pairs, timestamp),
    )
    return (
        (delta_history[0].delta_tree, corrupted_history_files)
        if delta_history
        else (ImmutableDeltaTree(), [])
    )


def get_history(hostname: HostName) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    return _get_history(hostname, filter_history_paths=lambda pairs: pairs)


def _sort_corrupted_history_files(corrupted_history_files: Sequence[Path]) -> Sequence[str]:
    return sorted(
        [str(fp.relative_to(cmk.utils.paths.omd_root)) for fp in set(corrupted_history_files)]
    )


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
) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    if "/" in hostname:
        return [], []  # just for security reasons

    history_files = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    ).history(host_name=hostname)

    cached_tree_loader = _CachedTreeLoader()
    history: list[HistoryEntry] = []
    filters = (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := get_permitted_inventory_paths(), list)
        else None
    )

    corrupted_deltas = []
    for previous, current in filter_history_paths(_get_pairs(history_files.paths)):
        if current.timestamp is None:
            continue

        cached_delta_tree_loader = _CachedDeltaTreeLoader(
            hostname,
            previous.timestamp,
            current.timestamp,
            filters,
        )

        if (cached_history_entry := cached_delta_tree_loader.get_cached_entry()) is not None:
            history.append(cached_history_entry)
            continue

        try:
            previous_tree = cached_tree_loader.get_tree(previous.path)
            current_tree = cached_tree_loader.get_tree(current.path)
        except (FileNotFoundError, ValueError):
            corrupted_deltas.append(cached_delta_tree_loader.path)
            continue

        if (
            history_entry := cached_delta_tree_loader.get_calculated_or_store_entry(
                previous_tree, current_tree
            )
        ) is not None:
            history.append(history_entry)

    return history, _sort_corrupted_history_files(list(history_files.corrupted) + corrupted_deltas)


@dataclass(frozen=True)
class _CachedTreeLoader:
    _lookup: dict[Path, ImmutableTree] = field(default_factory=dict)

    def get_tree(self, filepath: Path) -> ImmutableTree:
        if filepath == Path():
            return ImmutableTree()

        if filepath in self._lookup:
            return self._lookup[filepath]

        if not (tree := load_tree(filepath)):
            raise ValueError(tree)

        return self._lookup.setdefault(filepath, tree)


@dataclass(frozen=True)
class _CachedDeltaTreeLoader:
    hostname: HostName
    previous_timestamp: int | None
    current_timestamp: int
    # TODO Cleanup
    filters: Sequence[SDFilterChoice] | None

    @property
    def path(self) -> Path:
        return Path(
            cmk.utils.paths.inventory_delta_cache_dir,
            self.hostname,
            f"{self.previous_timestamp}_{self.current_timestamp}",
        )

    def get_cached_entry(self) -> HistoryEntry | None:
        try:
            cached_data = load_delta_cache(self.path)
        except MKGeneralException:
            return None

        if cached_data is None:
            return None

        new, changed, removed, delta_tree = cached_data
        return self._make_history_entry(new, changed, removed, delta_tree)

    def get_calculated_or_store_entry(
        self,
        previous_tree: ImmutableTree,
        current_tree: ImmutableTree,
    ) -> HistoryEntry | None:
        delta_tree = current_tree.difference(previous_tree)
        delta_stats = delta_tree.get_stats()
        new = delta_stats["new"]
        changed = delta_stats["changed"]
        removed = delta_stats["removed"]
        if new or changed or removed:
            save_delta_cache(self.path, (new, changed, removed, delta_tree))
            return self._make_history_entry(new, changed, removed, delta_tree)
        return None

    def _make_history_entry(
        self, new: int, changed: int, removed: int, delta_tree: ImmutableDeltaTree
    ) -> HistoryEntry | None:
        if self.filters is None:
            return HistoryEntry(self.current_timestamp, new, changed, removed, delta_tree)

        if not (filtered_delta_tree := delta_tree.filter(self.filters)):
            return None

        delta_stats = filtered_delta_tree.get_stats()
        return HistoryEntry(
            self.current_timestamp,
            delta_stats["new"],
            delta_stats["changed"],
            delta_stats["removed"],
            filtered_delta_tree,
        )
