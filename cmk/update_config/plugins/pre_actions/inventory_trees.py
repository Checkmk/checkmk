#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
import os
from collections.abc import Iterator, Sequence, Set
from logging import Logger
from pathlib import Path
from typing import override, Protocol

from cmk.ccc import store
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.inventory.paths import InventoryPaths
from cmk.update_config.internal import (
    ConflictMode,
    continue_per_users_choice,
    ExpiryVersion,
    PreUpdateAction,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry
from cmk.utils.paths import omd_root
from cmk.utils.render import approx_age

_LEGACY_HEAD = b"{'"
_HIDDEN_FILE_PREFIX = "."
_JSON_SUFFIX = ".json"
_GZ_SUFFIX = ".gz"
_JSON_GZ_SUFFIX = _JSON_SUFFIX + _GZ_SUFFIX
_SHOWN_FILES = 10


class ListHostNames(Protocol):
    def __call__(self) -> Set[str]: ...


class ListFileNames(Protocol):
    def __call__(self, directory: Path, /) -> Sequence[str]: ...


class ReadHead(Protocol):
    def __call__(self, file_path: Path, /) -> bytes: ...


class TransformationResults(Protocol):
    def load_durations(self) -> Sequence[float]: ...

    def remove(self) -> None: ...


def _list_configured_host_names() -> Set[str]:
    return frozenset(make_folder_tree(active_config).root_folder().all_hosts_recursively())


def _list_file_names(directory: Path) -> Sequence[str]:
    try:
        return os.listdir(directory)
    except FileNotFoundError, NotADirectoryError:
        return []


def _read_gzipped_head(file_path: Path) -> bytes:
    with gzip.open(file_path, "rb") as f:
        return f.read(len(_LEGACY_HEAD))


def _read_plain_head(file_path: Path) -> bytes:
    with file_path.open("rb") as f:
        return f.read(len(_LEGACY_HEAD))


def _read_head(file_path: Path) -> bytes:
    try:
        if file_path.name.endswith(_JSON_GZ_SUFFIX):
            return _read_gzipped_head(file_path)
        return _read_plain_head(file_path)
    except OSError, EOFError:
        return b""


def _parse_duration(raw_result: object) -> float | None:
    if not isinstance(raw_result, dict):
        return None
    match raw_result.get("duration"):
        case float() as duration:
            return duration
        case _:
            return None


def _parse_transformation_durations(raw_results: object) -> Sequence[float]:
    if not isinstance(raw_results, list):
        return []
    return [d for r in raw_results if (d := _parse_duration(r)) is not None]


class _TransformationResultsFile:
    def __init__(self, site_root: Path) -> None:
        self._file_path = site_root / "var/check_mk/inventory_transformation_results"

    def load_durations(self) -> Sequence[float]:
        return _parse_transformation_durations(
            store.load_object_from_file(self._file_path, default=[], debug=False)
        )

    def remove(self) -> None:
        self._file_path.unlink(missing_ok=True)


def _is_legacy_host_tree_file(file_path: Path, host_names: Set[str], read_head: ReadHead) -> bool:
    if not file_path.name.endswith((_JSON_SUFFIX, _JSON_GZ_SUFFIX)):
        return True
    if file_path.name.removesuffix(_GZ_SUFFIX) not in host_names:
        return False
    return read_head(file_path) == _LEGACY_HEAD


def _iter_legacy_host_tree_files(
    directory: Path, host_names: Set[str], list_file_names: ListFileNames, read_head: ReadHead
) -> Iterator[Path]:
    for name in list_file_names(directory):
        if not name.startswith(_HIDDEN_FILE_PREFIX) and _is_legacy_host_tree_file(
            directory / name, host_names, read_head
        ):
            yield directory / name


def _iter_legacy_history_tree_files(
    directory: Path, list_file_names: ListFileNames
) -> Iterator[Path]:
    for host_dir_name in list_file_names(directory):
        host_dir = directory / host_dir_name
        for name in list_file_names(host_dir):
            if not name.startswith(_HIDDEN_FILE_PREFIX) and not name.endswith(_JSON_SUFFIX):
                yield host_dir / name


def _find_legacy_tree_files(
    inventory_paths: InventoryPaths,
    *,
    host_names: Set[str],
    list_file_names: ListFileNames,
    read_head: ReadHead,
) -> Iterator[Path]:
    yield from _iter_legacy_host_tree_files(
        inventory_paths.inventory_dir, host_names, list_file_names, read_head
    )
    yield from _iter_legacy_host_tree_files(
        inventory_paths.status_data_dir, host_names, list_file_names, read_head
    )
    yield from _iter_legacy_history_tree_files(inventory_paths.archive_dir, list_file_names)
    yield from _iter_legacy_history_tree_files(inventory_paths.delta_cache_dir, list_file_names)


def _render_estimate(durations: Sequence[float], legacy_file_count: int) -> str:
    if not durations:
        return ""
    average = sum(durations) / len(durations)
    return (
        f"Measured on {len(durations)} converted trees, converting them takes about"
        f" {approx_age(average * legacy_file_count)}.\n"
    )


def _should_abort(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. "
                "Legacy inventory trees are not read after the update. Abort update? [A/c]\n"
            )


class LegacyInventoryTrees(PreUpdateAction):
    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        expiry_version: ExpiryVersion,
        inventory_paths: InventoryPaths,
        list_host_names: ListHostNames,
        list_file_names: ListFileNames,
        read_head: ReadHead,
        transformation_results: TransformationResults,
    ) -> None:
        super().__init__(
            name=name, title=title, sort_index=sort_index, expiry_version=expiry_version
        )
        self._inventory_paths = inventory_paths
        self._list_host_names = list_host_names
        self._list_file_names = list_file_names
        self._read_head = read_head
        self._transformation_results = transformation_results

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode, *, debug: bool) -> None:
        legacy_files = list(
            _find_legacy_tree_files(
                self._inventory_paths,
                host_names=self._list_host_names(),
                list_file_names=self._list_file_names,
                read_head=self._read_head,
            )
        )
        if not legacy_files:
            self._transformation_results.remove()
            return
        logger.warning(
            "%(count)d HW/SW Inventory trees still use the legacy file format, for example:\n"
            "%(file_paths)s\n"
            "Convert all of them with the Checkmk version you update from:\n"
            "  cmk-transform-inventory-trees --bundle-length %(count)d\n"
            "%(estimate)s"
            "Trees of removed hosts are not converted; delete them.",
            {
                "count": len(legacy_files),
                "estimate": _render_estimate(
                    self._transformation_results.load_durations(), len(legacy_files)
                ),
                "file_paths": "\n".join(
                    f"  {file_path}" for file_path in legacy_files[:_SHOWN_FILES]
                ),
            },
        )
        if _should_abort(conflict_mode).is_abort():
            raise MKUserError(None, "legacy HW/SW Inventory trees present")


pre_update_action_registry.register(
    LegacyInventoryTrees(
        name="legacy_inventory_trees",
        title="Check for HW/SW Inventory trees in the legacy file format",
        sort_index=5,
        expiry_version=ExpiryVersion.CMK_310,
        inventory_paths=InventoryPaths(omd_root),
        list_host_names=_list_configured_host_names,
        list_file_names=_list_file_names,
        read_head=_read_head,
        transformation_results=_TransformationResultsFile(omd_root),
    )
)
