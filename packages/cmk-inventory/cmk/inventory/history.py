#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import Error, OK, Result

from .delta import compare_trees, ImmutableDeltaTree
from .filtering import filter_delta_tree, SDFilterChoice
from .paths import (
    collect_files,
    InventoryPaths,
    parse_archive_timestamp,
    parse_delta_cache_timestamps,
    TreePath,
)
from .serialization import deserialize_delta_tree, SDRawDeltaTree, serialize_delta_tree
from .store import load_tree_from_tree_path
from .trees import ImmutableTree


@dataclass(frozen=True)
class HistoryDeltaPath:
    file_path: Path
    previous_timestamp: int
    current_timestamp: int


@dataclass(frozen=True)
class _HistoryPath:
    tree_path: TreePath
    timestamp: int


@dataclass(frozen=True, kw_only=True)
class HistoryArchivePath:
    previous: _HistoryPath | None
    current: _HistoryPath

    @property
    def previous_timestamp(self) -> int:
        return -1 if self.previous is None else self.previous.timestamp

    @property
    def current_timestamp(self) -> int:
        return self.current.timestamp


@dataclass(frozen=True, kw_only=True)
class HistoryEntry:
    previous_timestamp: int
    current_timestamp: int
    new: int
    changed: int
    removed: int
    delta_tree: ImmutableDeltaTree

    @classmethod
    def from_raw(
        cls,
        *,
        previous_timestamp: int,
        current_timestamp: int,
        raw: tuple[int, int, int, SDRawDeltaTree],
    ) -> HistoryEntry:
        new, changed, removed, raw_delta_tree = raw
        return cls(
            previous_timestamp=previous_timestamp,
            current_timestamp=current_timestamp,
            new=new,
            changed=changed,
            removed=removed,
            delta_tree=deserialize_delta_tree(raw_delta_tree),
        )

    @classmethod
    def from_delta_tree(
        cls,
        *,
        previous_timestamp: int,
        current_timestamp: int,
        delta_tree: ImmutableDeltaTree,
    ) -> HistoryEntry:
        delta_stats = delta_tree.get_stats()
        return cls(
            previous_timestamp=previous_timestamp,
            current_timestamp=current_timestamp,
            new=delta_stats["new"],
            changed=delta_stats["changed"],
            removed=delta_stats["removed"],
            delta_tree=delta_tree,
        )


@dataclass(frozen=True)
class History:
    entries: Sequence[HistoryEntry]
    corrupted: Sequence[Path]


class HistoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)
        self._lookup: dict[tuple[Path, Path], ImmutableTree] = {}

    def _collect_paths_from_delta_cache(
        self, host_name: HostName
    ) -> Iterator[Result[HistoryDeltaPath, Path]]:
        for file_path in collect_files(self.inv_paths.delta_cache_host(host_name)):
            try:
                previous_timestamp, current_timestamp = parse_delta_cache_timestamps(file_path)
            except ValueError:
                yield Error(file_path)
                continue

            yield OK(
                HistoryDeltaPath(
                    file_path=file_path,
                    previous_timestamp=previous_timestamp,
                    current_timestamp=current_timestamp,
                )
            )

    def _collect_paths_from_archive(
        self, host_name: HostName
    ) -> Iterator[Result[_HistoryPath, Path]]:
        try:
            file_paths = list(self.inv_paths.archive_host(host_name).iterdir())
        except FileNotFoundError:
            return

        for file_path in file_paths:
            try:
                yield OK(
                    _HistoryPath(
                        tree_path=TreePath.from_archive_or_delta_cache_file_path(file_path),
                        timestamp=parse_archive_timestamp(file_path),
                    )
                )
            except ValueError:
                yield Error(file_path)

        tree_path = self.inv_paths.inventory_tree(host_name)
        try:
            yield OK(
                _HistoryPath(
                    tree_path=tree_path,
                    timestamp=int(tree_path.path.stat().st_mtime),
                )
            )
        except FileNotFoundError:
            # TODO CMK-23408
            with contextlib.suppress(FileNotFoundError):
                yield OK(
                    _HistoryPath(
                        tree_path=tree_path,
                        timestamp=int(tree_path.legacy.stat().st_mtime),
                    )
                )

    def _collect_history_paths(
        self, *, host_name: HostName
    ) -> Iterator[Result[HistoryDeltaPath | HistoryArchivePath, Path]]:
        known_paths: dict[tuple[int, int], HistoryDeltaPath | HistoryArchivePath] = {}
        for result_from_delta_cache in self._collect_paths_from_delta_cache(host_name):
            if result_from_delta_cache.is_ok():
                known_paths[
                    (
                        result_from_delta_cache.ok.previous_timestamp,
                        result_from_delta_cache.ok.current_timestamp,
                    )
                ] = result_from_delta_cache.ok
            else:
                yield result_from_delta_cache

        results_from_archive = list(self._collect_paths_from_archive(host_name))
        sorted_paths_from_archive = sorted(
            [r.ok for r in results_from_archive if r.is_ok()], key=lambda p: p.timestamp
        )
        previous_paths: Sequence[_HistoryPath | None] = [None, *sorted_paths_from_archive]
        for previous, current in zip(previous_paths, sorted_paths_from_archive):
            previous_timestamp = -1 if previous is None else previous.timestamp
            if (key := (previous_timestamp, current.timestamp)) not in known_paths:
                known_paths[key] = HistoryArchivePath(previous=previous, current=current)

        for key in sorted(known_paths, key=lambda k: k[1]):
            yield OK(known_paths[key])

        for result_from_archive in results_from_archive:
            if result_from_archive.is_error():
                yield Error(result_from_archive.error)

    def _lookup_tree(self, path: _HistoryPath | None) -> ImmutableTree:
        if path is None:
            return ImmutableTree()

        key = (path.tree_path.path, path.tree_path.legacy)
        if key not in self._lookup:
            self._lookup[key] = load_tree_from_tree_path(path.tree_path)
        return self._lookup[key]

    def _load_history_entry(
        self, *, host_name: HostName, path: HistoryDeltaPath | HistoryArchivePath
    ) -> Result[HistoryEntry, Sequence[Path]]:
        match path:
            case HistoryDeltaPath():
                try:
                    raw = (
                        json.loads(store.load_text_from_file(path.file_path))
                        if path.file_path.suffix == ".json"
                        else store.load_object_from_file(path.file_path, default=None)
                    )
                except MKGeneralException:
                    return Error([path.file_path])

                if raw is None:
                    return Error([path.file_path])

                return OK(
                    HistoryEntry.from_raw(
                        previous_timestamp=path.previous_timestamp,
                        current_timestamp=path.current_timestamp,
                        raw=raw,
                    )
                )

            case HistoryArchivePath():
                entry = HistoryEntry.from_delta_tree(
                    previous_timestamp=path.previous_timestamp,
                    current_timestamp=path.current_timestamp,
                    delta_tree=compare_trees(
                        self._lookup_tree(path.current),
                        self._lookup_tree(path.previous),
                    ),
                )

                if entry.new or entry.changed or entry.removed:
                    if path.current.tree_path != self.inv_paths.inventory_tree(host_name):
                        self._save_history_entry(host_name=host_name, history_entry=entry)
                    return OK(entry)

                return Error(
                    [
                        path.current.tree_path.path,
                        path.current.tree_path.legacy,
                        path.current.tree_path.path,
                        path.current.tree_path.legacy,
                    ]
                )

    def _save_history_entry(self, *, host_name: HostName, history_entry: HistoryEntry) -> None:
        delta_cache_tree = self.inv_paths.delta_cache_tree(
            host_name,
            history_entry.previous_timestamp,
            history_entry.current_timestamp,
        )
        self.inv_paths.delta_cache_host(host_name).mkdir(parents=True, exist_ok=True)
        store.save_text_to_file(
            delta_cache_tree.path,
            json.dumps(
                (
                    history_entry.new,
                    history_entry.changed,
                    history_entry.removed,
                    serialize_delta_tree(history_entry.delta_tree),
                )
            ),
        )
        delta_cache_tree.legacy.unlink(missing_ok=True)

    def load(
        self,
        host_name: HostName,
        *,
        history_paths_filter: Callable[
            [Sequence[HistoryDeltaPath | HistoryArchivePath]],
            Sequence[HistoryDeltaPath | HistoryArchivePath],
        ],
        delta_tree_filters: Sequence[SDFilterChoice] | None,
    ) -> History:
        paths = []
        corrupted: set[Path] = set()
        for path_result in self._collect_history_paths(host_name=host_name):
            if path_result.is_ok():
                paths.append(path_result.ok)
            else:
                corrupted.add(path_result.error)

        entries = []
        for path in history_paths_filter(paths):
            if (entry_result := self._load_history_entry(host_name=host_name, path=path)).is_ok():
                entries.append(entry_result.ok)
            else:
                corrupted.update(entry_result.error)

        if delta_tree_filters is None:
            return History(entries=entries, corrupted=list(corrupted))

        return History(
            entries=[
                HistoryEntry.from_delta_tree(
                    previous_timestamp=e.previous_timestamp,
                    current_timestamp=e.current_timestamp,
                    delta_tree=d,
                )
                for e in entries
                if (d := filter_delta_tree(e.delta_tree, delta_tree_filters))
            ],
            corrupted=list(corrupted),
        )
