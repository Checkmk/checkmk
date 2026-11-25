#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import math
import os
import sys
from collections.abc import Callable, Iterator, Sequence, Set
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName

from .paths import DeltaCachePath, Paths, TreePath, TreePathGz
from .structured_data import transform


@dataclass(frozen=True)
class _HostTreePath:
    host_name: str
    tree_path: TreePath | TreePathGz | DeltaCachePath
    stat: os.stat_result


_HIDDEN_FILE_PREFIX = "."
_JSON_SUFFIXES = (".json", ".json.gz")


def _collect_file_paths(directory: Path) -> Set[Path]:
    try:
        return frozenset(
            fp for fp in directory.iterdir() if not fp.name.startswith(_HIDDEN_FILE_PREFIX)
        )
    except FileNotFoundError:
        return frozenset()


def _compute_file_path_stat(file_path: Path) -> os.stat_result | None:
    try:
        return file_path.stat()
    except FileNotFoundError:
        return None


def _iter_current_tree_paths(
    inv_paths: Paths, host_name: HostName
) -> Iterator[TreePath | TreePathGz]:
    yield inv_paths.inventory_tree(host_name)
    yield inv_paths.inventory_tree_gz(host_name)
    yield inv_paths.status_data_tree(host_name)


def _compute_host_tree_path(
    host_name: HostName, tree_path: TreePath | TreePathGz, current_file_paths: Set[Path]
) -> _HostTreePath | None:
    if tree_path.path in current_file_paths or tree_path.legacy not in current_file_paths:
        return None
    if stat := _compute_file_path_stat(tree_path.legacy):
        return _HostTreePath(str(host_name), tree_path, stat)
    return None


def _iter_current_host_tree_paths(
    inv_paths: Paths, current_file_paths: Set[Path], all_host_names: Sequence[str]
) -> Iterator[_HostTreePath]:
    for raw_host_name in all_host_names:
        host_name = HostName(raw_host_name)
        for tree_path in _iter_current_tree_paths(inv_paths, host_name):
            if host_tree_path := _compute_host_tree_path(host_name, tree_path, current_file_paths):
                yield host_tree_path


def _collect_history_file_paths(directory: Path) -> Iterator[tuple[str, Path]]:
    try:
        host_dirs = list(directory.iterdir())
    except FileNotFoundError:
        host_dirs = []
    for host_dir in host_dirs:
        try:
            file_paths = list(host_dir.iterdir())
        except (FileNotFoundError, NotADirectoryError):
            file_paths = []
        for file_path in file_paths:
            yield host_dir.name, file_path


def _iter_history_host_tree_paths(inv_paths: Paths) -> Iterator[_HostTreePath]:
    for raw_host_name, file_path in _collect_history_file_paths(inv_paths.archive_dir):
        tree_path = TreePath.from_archive_or_delta_cache_file_path(file_path)
        if stat := _compute_file_path_stat(tree_path.legacy):
            yield _HostTreePath(raw_host_name, tree_path, stat)

    for raw_host_name, file_path in _collect_history_file_paths(inv_paths.delta_cache_dir):
        delta_cache_path = DeltaCachePath.from_archive_or_delta_cache_file_path(file_path)
        if stat := _compute_file_path_stat(delta_cache_path.legacy):
            yield _HostTreePath(raw_host_name, delta_cache_path, stat)


def _find_legacy_trees_of_removed_hosts(
    inv_paths: Paths, current_file_paths: Set[Path], all_host_names: Sequence[str]
) -> Sequence[Path]:
    legacy_trees_of_hosts = {
        tree_path.legacy
        for raw_host_name in all_host_names
        for tree_path in _iter_current_tree_paths(inv_paths, HostName(raw_host_name))
    }
    return sorted(
        fp
        for fp in current_file_paths
        if not fp.name.endswith(_JSON_SUFFIXES) and fp not in legacy_trees_of_hosts
    )


def _collect_host_tree_paths_and_legacy_trees_of_removed_hosts(
    omd_root: Path, all_host_names: Sequence[str]
) -> tuple[Sequence[_HostTreePath], Sequence[Path]]:
    inv_paths = Paths(omd_root)
    current_file_paths = _collect_file_paths(inv_paths.inventory_dir) | _collect_file_paths(
        inv_paths.status_data_dir
    )
    return (
        [
            *_iter_current_host_tree_paths(inv_paths, current_file_paths, all_host_names),
            *_iter_history_host_tree_paths(inv_paths),
        ],
        _find_legacy_trees_of_removed_hosts(inv_paths, current_file_paths, all_host_names),
    )


class TransformationResult(TypedDict):
    host_name: str
    path: str
    duration: float
    size: int | float


class TransformationResultsStore:
    def __init__(self, omd_root: Path) -> None:
        self.file_path = omd_root / "var/check_mk/inventory_transformation_results"

    def load(self) -> Sequence[TransformationResult]:
        return [
            TransformationResult(
                host_name=r["host_name"],
                path=r["path"],
                duration=r["duration"],
                size=r["size"],
            )
            for r in cmk.ccc.store.load_object_from_file(self.file_path, default=[])
        ]

    def save(self, transformation_results: Sequence[TransformationResult]) -> None:
        cmk.ccc.store.save_object_to_file(self.file_path, transformation_results)


def _render_duration(duration: int | float) -> str:
    return f"{duration:.2f} seconds"


def _render_size(size: int | float) -> str:
    if size > 1000**3:
        return f"{size / 1000**3:.2f} GB"
    if size > 1000**2:
        return f"{size / 1000**2:.2f} MB"
    if size > 1000:
        return f"{size / 1000:.2f} KB"
    return f"{size} B"


def _show_results(
    host_tree_paths: Sequence[_HostTreePath],
    legacy_trees_of_removed_hosts: Sequence[Path],
    transformation_results: Sequence[TransformationResult],
) -> None:
    sys.stdout.write("=== Transformation summary ===\n")
    sys.stdout.write(f"Total #files: {len(host_tree_paths)}\n")
    sys.stdout.write(f"Total #transformed files: {len(transformation_results)}\n")

    overall_duration = sum(r["duration"] for r in transformation_results)
    sys.stdout.write(f"Total duration: {_render_duration(overall_duration)}\n")

    if transformation_results:
        overall_size = sum(r["size"] for r in transformation_results)
        sys.stdout.write(
            f"Average size: {_render_size(overall_size / len(transformation_results))}\n"
        )

    for result in transformation_results:
        sys.stdout.write("------------------------------\n")
        sys.stdout.write(f"Host name: {result['host_name']}\n")
        sys.stdout.write(f"Path: {result['path']}\n")
        sys.stdout.write(f"Duration: {_render_duration(result['duration'])}\n")
        sys.stdout.write(f"Size: {_render_size(result['size'])}\n")

    if legacy_trees_of_removed_hosts:
        sys.stdout.write("=== Legacy trees of removed hosts ===\n")
        sys.stdout.write(
            "These trees belong to no host and are not transformed. Delete these files before"
            " updating to Checkmk 3.0:\n"
        )
        for file_path in legacy_trees_of_removed_hosts:
            sys.stdout.write(f"- {file_path}\n")


def _compute_bundle_size(bundle_length: int, pending_count: int, transformed_count: int) -> int:
    if bundle_length > 0:
        return bundle_length
    return math.ceil((pending_count + transformed_count) / 200)


def _transform_host_tree_path(
    host_tree_path: _HostTreePath, clock: Callable[[], float]
) -> TransformationResult:
    start = clock()
    transform(host_tree_path.tree_path, host_tree_path.stat.st_mtime)
    return TransformationResult(
        host_name=host_tree_path.host_name,
        path=str(host_tree_path.tree_path.legacy),
        duration=clock() - start,
        size=host_tree_path.stat.st_size,
    )


def _transform_bundle(
    logger: logging.Logger,
    host_tree_paths: Sequence[_HostTreePath],
    bundle_size: int,
    clock: Callable[[], float],
) -> Sequence[TransformationResult]:
    transformation_results: list[TransformationResult] = []
    for host_tree_path in host_tree_paths:
        if len(transformation_results) >= bundle_size:
            break
        try:
            transformation_results.append(_transform_host_tree_path(host_tree_path, clock))
        except Exception:
            logger.exception("Failed to transform %s", host_tree_path.tree_path.legacy)
    return transformation_results


def transform_inventory_trees(
    *,
    logger: logging.Logger,
    omd_root: Path,
    show_results: bool,
    bundle_length: int,
    filter_host_names: Sequence[str],
    all_host_names: Sequence[str],
    clock: Callable[[], float],
) -> int:
    host_tree_paths, legacy_trees_of_removed_hosts = (
        _collect_host_tree_paths_and_legacy_trees_of_removed_hosts(omd_root, all_host_names)
    )
    if filter_host_names:
        host_tree_paths = [htp for htp in host_tree_paths if htp.host_name in filter_host_names]

    transformation_results_store = TransformationResultsStore(omd_root)
    transformation_results = transformation_results_store.load()

    if show_results:
        _show_results(host_tree_paths, legacy_trees_of_removed_hosts, transformation_results)
        return 0

    bundle_size = (
        len(host_tree_paths)
        if filter_host_names
        else _compute_bundle_size(bundle_length, len(host_tree_paths), len(transformation_results))
    )
    new_transformation_results = _transform_bundle(logger, host_tree_paths, bundle_size, clock)

    if len_results := len(new_transformation_results):
        logger.info("Transformed %s inventory trees", len_results)
    transformation_results_store.save([*transformation_results, *new_transformation_results])

    return 0
