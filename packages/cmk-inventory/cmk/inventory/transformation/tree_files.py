#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import math
import os
import sys
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

import cmk.ccc.store
from cmk.ccc.hostaddress import HostName
from cmk.inventory.paths import collect_files, InventoryPaths, TreePath, TreePathGz
from cmk.inventory.store import parse_from_gzipped, save_raw_tree, save_raw_tree_gz

_KILO = 1000
_NUMBER_OF_BUNDLES = 200


def _transform_tree_path(tree_path: TreePath, mtime: float) -> None:
    with cmk.ccc.store.locked(tree_path.path), cmk.ccc.store.locked(tree_path.legacy):
        if raw_tree := cmk.ccc.store.load_object_from_file(tree_path.legacy, default=None):
            save_raw_tree(tree_path, raw_tree)
            os.utime(tree_path.path, (mtime, mtime))
    tree_path.legacy.unlink(missing_ok=True)


def _transform_tree_path_gz(tree_path_gz: TreePathGz, mtime: float) -> None:
    with cmk.ccc.store.locked(tree_path_gz.path), cmk.ccc.store.locked(tree_path_gz.legacy):
        if gzipped := cmk.ccc.store.load_bytes_from_file(tree_path_gz.legacy, default=b""):
            save_raw_tree_gz(tree_path_gz, parse_from_gzipped(gzipped))
            os.utime(tree_path_gz.path, (mtime, mtime))
    tree_path_gz.legacy.unlink(missing_ok=True)


def transform(tree_path: TreePath | TreePathGz, mtime: float) -> None:
    match tree_path:
        case TreePath():
            _transform_tree_path(tree_path, mtime)
        case TreePathGz():
            _transform_tree_path_gz(tree_path, mtime)


@dataclass(frozen=True)
class _HostTreePath:
    host_name: str
    tree_path: TreePath | TreePathGz
    stat: os.stat_result


def _collect_tree_file_paths(directory: Path) -> Sequence[Path]:
    return [fp for fp in collect_files(directory) if fp.name != ".last"]


def _compute_file_path_stat(file_path: Path) -> os.stat_result | None:
    try:
        return file_path.stat()
    except FileNotFoundError:
        return None


def _compute_host_tree_path_or_unknown_file_path(
    host_name: HostName, tree_path: TreePath | TreePathGz, all_file_paths: Sequence[Path]
) -> _HostTreePath | Path | None:
    if tree_path.path in all_file_paths:
        return None
    if tree_path.legacy in all_file_paths and (stat := _compute_file_path_stat(tree_path.legacy)):
        return _HostTreePath(str(host_name), tree_path, stat)
    return tree_path.legacy


def _iter_host_tree_paths_or_unknown_file_paths(
    omd_root: Path, all_host_names: Sequence[str]
) -> Iterator[_HostTreePath | Path]:
    inv_paths = InventoryPaths(omd_root)

    inventory_file_paths = _collect_tree_file_paths(inv_paths.inventory_dir)
    status_data_file_paths = _collect_tree_file_paths(inv_paths.status_data_dir)

    for raw_host_name in all_host_names:
        host_name = HostName(raw_host_name)
        if path := _compute_host_tree_path_or_unknown_file_path(
            host_name, inv_paths.inventory_tree(host_name), inventory_file_paths
        ):
            yield path
        if path := _compute_host_tree_path_or_unknown_file_path(
            host_name, inv_paths.inventory_tree_gz(host_name), inventory_file_paths
        ):
            yield path
        if path := _compute_host_tree_path_or_unknown_file_path(
            host_name, inv_paths.status_data_tree(host_name), status_data_file_paths
        ):
            yield path

    for host_dir in list(collect_files(inv_paths.archive_dir)) + list(
        collect_files(inv_paths.delta_cache_dir)
    ):
        try:
            file_paths = list(host_dir.iterdir())
        except FileNotFoundError, NotADirectoryError:
            file_paths = []

        raw_host_name = host_dir.name
        for file_path in file_paths:
            tree_path = TreePath.from_archive_or_delta_cache_file_path(file_path)
            if stat := _compute_file_path_stat(tree_path.legacy):
                yield _HostTreePath(raw_host_name, tree_path, stat)


def _collect_host_tree_paths_or_unknown_file_paths(
    omd_root: Path, all_host_names: Sequence[str]
) -> tuple[Sequence[_HostTreePath], Sequence[Path]]:
    host_tree_paths = []
    unknown_file_paths = []
    for host_tree_path_or_unknown_file_path in _iter_host_tree_paths_or_unknown_file_paths(
        omd_root, all_host_names
    ):
        match host_tree_path_or_unknown_file_path:
            case _HostTreePath():
                host_tree_paths.append(host_tree_path_or_unknown_file_path)
            case Path():
                unknown_file_paths.append(host_tree_path_or_unknown_file_path)
    return host_tree_paths, unknown_file_paths


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
    if size > _KILO**3:
        return f"{size / _KILO**3:.2f} GB"
    if size > _KILO**2:
        return f"{size / _KILO**2:.2f} MB"
    if size > _KILO:
        return f"{size / _KILO:.2f} KB"
    return f"{size} B"


def _show_results(
    host_tree_paths: Sequence[_HostTreePath],
    unknown_file_paths: Sequence[Path],
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

    if unknown_file_paths:
        sys.stdout.write("=== Unknown file paths ===\n")
        info = [
            (
                "Please check the following list of inventory file paths. These files may be belong"
                " to removed hosts or could not be assigned to the current list of available hosts."
                " In the first case you can safely remove these files. In the second case they may"
                " be transformed with the next go or you can also try to transform these files via"
                " 'cmk-transform-inventory-trees --host-name <HOST> [<HOST> ...]'."
            )
        ]
        sys.stdout.write(f"{'\n'.join(info)}\n")
        for unknown_file_path in unknown_file_paths:
            sys.stdout.write("- %r\n" % unknown_file_path)


def _compute_bundle(
    bundle_length: int, host_tree_paths: Sequence[_HostTreePath]
) -> Sequence[_HostTreePath]:
    if not host_tree_paths:
        return []
    if bundle_length > 0:
        return host_tree_paths[:bundle_length]
    return host_tree_paths[: math.ceil(len(host_tree_paths) / _NUMBER_OF_BUNDLES)]


def _transform_host_tree_path(host_tree_path: _HostTreePath) -> TransformationResult:
    now = time.time()
    transform(host_tree_path.tree_path, host_tree_path.stat.st_mtime)
    return TransformationResult(
        host_name=host_tree_path.host_name,
        path=str(host_tree_path.tree_path.legacy),
        duration=int(time.time() - now),
        size=host_tree_path.stat.st_size,
    )


def _collect_selected_host_tree_paths_or_unknown_file_paths(
    omd_root: Path, filter_host_names: Sequence[str], all_host_names: Sequence[str]
) -> tuple[Sequence[_HostTreePath], Sequence[Path]]:
    host_tree_paths, unknown_file_paths = _collect_host_tree_paths_or_unknown_file_paths(
        omd_root, all_host_names
    )
    if filter_host_names:
        host_tree_paths = [htp for htp in host_tree_paths if htp.host_name in filter_host_names]
    return host_tree_paths, unknown_file_paths


def show_transformation_results(
    *,
    omd_root: Path,
    filter_host_names: Sequence[str],
    all_host_names: Sequence[str],
) -> int:
    host_tree_paths, unknown_file_paths = _collect_selected_host_tree_paths_or_unknown_file_paths(
        omd_root, filter_host_names, all_host_names
    )
    _show_results(host_tree_paths, unknown_file_paths, TransformationResultsStore(omd_root).load())
    return 0


def transform_inventory_trees(
    *,
    logger: logging.Logger,
    omd_root: Path,
    bundle_length: int,
    filter_host_names: Sequence[str],
    all_host_names: Sequence[str],
) -> int:
    host_tree_paths, _unknown_file_paths = _collect_selected_host_tree_paths_or_unknown_file_paths(
        omd_root, filter_host_names, all_host_names
    )

    transformation_results_store = TransformationResultsStore(omd_root)
    transformation_results = transformation_results_store.load()

    if filter_host_names:
        to_be_transformed = host_tree_paths
    else:
        to_be_transformed = _compute_bundle(bundle_length, host_tree_paths)

    new_transformation_results = []
    for host_tree_path in to_be_transformed:
        new_transformation_results.append(_transform_host_tree_path(host_tree_path))

    if len_results := len(new_transformation_results):
        logger.info("Transformed %(tree_count)s inventory trees", {"tree_count": len_results})
    transformation_results_store.save(list(transformation_results) + new_transformation_results)

    return 0
