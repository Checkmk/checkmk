#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from cmk.ccc.hostaddress import HostName

from .config import (
    InvCleanupParams,
    InvCleanupParamsChoice,
    InvCleanupParamsDefaultCombined,
    InvCleanupParamsOfHosts,
    matches,
)
from .paths import Paths as InventoryPaths
from .paths import TreePath, TreePathGz


@dataclass(frozen=True, kw_only=True)
class _File:
    path: Path
    timestamp: int


@dataclass(frozen=True, kw_only=True)
class _ArchiveBundle:
    previous: Path
    current: Path
    delta_cache: _File | None
    timestamp: int


class _CleanupParams(Protocol):
    def file_is_too_old(self, now: int, timestamp: int, /) -> bool: ...

    def compute_removable_bundles(
        self, now: int, bundles: Sequence[_File | _ArchiveBundle], /
    ) -> Sequence[_File | _ArchiveBundle]: ...


@dataclass(frozen=True)
class _ParamsFileAge:
    file_age: int

    def file_is_too_old(self, now: int, timestamp: int) -> bool:
        return now - self.file_age >= timestamp

    def compute_removable_bundles(
        self, now: int, bundles: Sequence[_File | _ArchiveBundle]
    ) -> Sequence[_File | _ArchiveBundle]:
        return [b for b in bundles if self.file_is_too_old(now, b.timestamp)]


@dataclass(frozen=True)
class _ParamsNumberHistoryEntries:
    number_of_history_entries: int

    def file_is_too_old(self, _now: int, _timestamp: int) -> bool:
        return False

    def compute_removable_bundles(
        self,
        _now: int,
        bundles: Sequence[_File | _ArchiveBundle],
    ) -> Sequence[_File | _ArchiveBundle]:
        return sorted(bundles, key=lambda b: b.timestamp, reverse=True)[
            self.number_of_history_entries :
        ]


@dataclass(frozen=True, kw_only=True)
class _ParamFileAgeNumberHistoryEntries:
    strategy: Literal["and", "or"]
    param_file_age: _ParamsFileAge
    param_number_of_history_entries: _ParamsNumberHistoryEntries

    def file_is_too_old(self, now: int, timestamp: int) -> bool:
        return self.param_file_age.file_is_too_old(now, timestamp)

    def compute_removable_bundles(
        self, now: int, bundles: Sequence[_File | _ArchiveBundle]
    ) -> Sequence[_File | _ArchiveBundle]:
        too_old_bundles = self.param_file_age.compute_removable_bundles(now, bundles)
        cut_off_bundles = self.param_number_of_history_entries.compute_removable_bundles(
            now, bundles
        )
        match self.strategy:
            case "and":
                return list(set(too_old_bundles).intersection(cut_off_bundles))
            case "or":
                return list(set(too_old_bundles).union(cut_off_bundles))


def _compute_params(
    params: InvCleanupParamsChoice,
) -> _CleanupParams:
    match params[0]:
        case "file_age":
            return _ParamsFileAge(params[1])
        case "number_of_history_entries":
            return _ParamsNumberHistoryEntries(params[1])
        case "combined":
            combined_params = params[1]
            return _ParamFileAgeNumberHistoryEntries(
                strategy=combined_params["strategy"],
                param_file_age=_ParamsFileAge(combined_params["file_age"]),
                param_number_of_history_entries=_ParamsNumberHistoryEntries(
                    combined_params["number_of_history_entries"]
                ),
            )


def _compute_host_params(
    hosts_params: Sequence[InvCleanupParamsOfHosts],
    default_params: InvCleanupParamsDefaultCombined | None,
    host_name: HostName,
) -> _CleanupParams | None:
    for host_params in hosts_params:
        for regex_or_name in host_params["regex_or_explicit"]:
            if matches(regex_or_name=regex_or_name, host_name=host_name):
                return _compute_params(host_params["parameters"])
    return (
        None
        if default_params is None
        else _ParamFileAgeNumberHistoryEntries(
            strategy=default_params["strategy"],
            param_file_age=_ParamsFileAge(default_params["file_age"]),
            param_number_of_history_entries=_ParamsNumberHistoryEntries(
                default_params["number_of_history_entries"]
            ),
        )
    )


@dataclass(frozen=True, kw_only=True)
class _FilePathsOfHost:
    inventory_tree: TreePath
    inventory_tree_gz: TreePathGz
    status_data_tree: TreePath
    archive_file_paths: Sequence[Path]
    delta_cache_file_paths: Sequence[Path]


def _collect_files_from_directory(directory: Path) -> Sequence[Path]:
    try:
        return list(directory.iterdir())
    except FileNotFoundError:
        return []


def _compute_timestamp_from_file_path(file_path: Path) -> int | None:
    try:
        return int(file_path.stat().st_mtime)
    except FileNotFoundError:
        return None


def _compute_timestamp_from_archive_file_name(file_path: Path) -> int | None:
    try:
        return int(file_path.with_suffix("").name)
    except ValueError:
        return None


def _compute_timestamps_from_delta_cache_file_name(file_path: Path) -> tuple[int, int] | None:
    try:
        previous_name, current_name = file_path.with_suffix("").name.split("_")
        return (
            -1 if previous_name == "None" else int(previous_name),
            int(current_name),
        )
    except ValueError:
        return None


@dataclass(frozen=True, kw_only=True)
class _AbandonedFilesOfHost:
    host_name: str
    folders_and_files: Mapping[Path, Sequence[_File]]
    files: Sequence[_File]

    def compute_youngest_timestamp(self) -> int | None:
        timestamps: set[int] = set()
        if self.files:
            timestamps.update(f.timestamp for f in self.files)
        if self.folders_and_files:
            timestamps.update(f.timestamp for fs in self.folders_and_files.values() for f in fs)
        return max(timestamps) if timestamps else None


@dataclass(frozen=True, kw_only=True)
class _ClassifiedFilePaths:
    by_host: Mapping[HostName, _FilePathsOfHost]
    abandoned_host_files: Sequence[_AbandonedFilesOfHost]
    abandoned_files: Sequence[_File]


def _compute_classified_file_paths(
    inventory_paths: InventoryPaths, host_names: Sequence[HostName]
) -> _ClassifiedFilePaths:
    if not host_names:
        return _ClassifiedFilePaths(by_host={}, abandoned_files=[], abandoned_host_files=[])

    # Construct all files of known hosts
    file_paths_by_host = {
        h: _FilePathsOfHost(
            inventory_tree=inventory_paths.inventory_tree(h),
            inventory_tree_gz=inventory_paths.inventory_tree_gz(h),
            status_data_tree=inventory_paths.status_data_tree(h),
            archive_file_paths=_collect_files_from_directory(inventory_paths.archive_host(h)),
            delta_cache_file_paths=_collect_files_from_directory(
                inventory_paths.delta_cache_host(h)
            ),
        )
        for h in host_names
    }

    # Compute all unknown archive files
    abandoned_folders_and_files_by_host: dict[str, dict[Path, list[_File]]] = {}
    for file_path in set(inventory_paths.archive_dir.glob("*/*")).difference(
        fp for fps in file_paths_by_host.values() for fp in fps.archive_file_paths
    ):
        if (timestamp := _compute_timestamp_from_archive_file_name(file_path)) is not None:
            abandoned_folders_and_files_by_host.setdefault(file_path.parent.name, {}).setdefault(
                file_path.parent, []
            ).append(_File(path=file_path, timestamp=timestamp))

    # Compute all unknown delta cache files
    for file_path in set(inventory_paths.delta_cache_dir.glob("*/*")).difference(
        fp for fps in file_paths_by_host.values() for fp in fps.delta_cache_file_paths
    ):
        if (timestamps := _compute_timestamps_from_delta_cache_file_name(file_path)) is not None:
            abandoned_folders_and_files_by_host.setdefault(file_path.parent.name, {}).setdefault(
                file_path.parent, []
            ).append(_File(path=file_path, timestamp=timestamps[-1]))

    # Construct inventory or status data tree files of unknown hosts
    # (with archive or delta cache files)
    abandoned_tree_files_by_host: dict[str, list[_File]] = {}
    for raw_host_name in abandoned_folders_and_files_by_host:
        host_name = HostName(raw_host_name)
        inventory_tree = inventory_paths.inventory_tree(host_name)
        inventory_tree_gz = inventory_paths.inventory_tree_gz(host_name)
        status_data_tree = inventory_paths.status_data_tree(host_name)
        for file_path in [
            inventory_tree.path,
            inventory_tree.legacy,
            inventory_tree_gz.path,
            inventory_tree_gz.legacy,
            status_data_tree.path,
            status_data_tree.legacy,
        ]:
            if (timestamp := _compute_timestamp_from_file_path(file_path)) is not None:
                abandoned_tree_files_by_host.setdefault(raw_host_name, []).append(
                    _File(path=file_path, timestamp=timestamp)
                )

    return _ClassifiedFilePaths(
        by_host=file_paths_by_host,
        abandoned_host_files=[
            _AbandonedFilesOfHost(
                host_name=host_name,
                files=abandoned_tree_files_by_host.get(host_name, []),
                folders_and_files=folders_and_files,
            )
            for host_name, folders_and_files in abandoned_folders_and_files_by_host.items()
        ],
        # Construct remaining inventory or status data tree files of unknown hosts
        # (without archive or delta cache files)
        abandoned_files=[
            _File(path=file_path, timestamp=timestamp)
            for file_path in (
                set(inventory_paths.inventory_dir.glob("[!.]*"))
                .union(inventory_paths.status_data_dir.glob("*"))
                .difference(
                    fp
                    for fps in file_paths_by_host.values()
                    for fp in [
                        fps.inventory_tree.path,
                        fps.inventory_tree.legacy,
                        fps.inventory_tree_gz.path,
                        fps.inventory_tree_gz.legacy,
                        fps.status_data_tree.path,
                        fps.status_data_tree.legacy,
                    ]
                )
                .difference(f.path for fs in abandoned_tree_files_by_host.values() for f in fs)
            )
            if (timestamp := _compute_timestamp_from_file_path(file_path)) is not None
        ],
    )


def _compute_timestamp_from_tree_path(tree_path: TreePath) -> int | None:
    if (ts := _compute_timestamp_from_file_path(tree_path.path)) is not None:
        return ts
    return _compute_timestamp_from_file_path(tree_path.legacy)


@dataclass(frozen=True, kw_only=True)
class _ClassifiedHistoryFiles:
    delta_cache_from_inventory_tree: Path | None
    bundles: Sequence[_File | _ArchiveBundle]
    single_archive_files: Sequence[_File]


def _compute_classified_history_files(
    *,
    inventory_tree: TreePath,
    archive_file_paths: Sequence[Path],
    delta_cache_file_paths: Sequence[Path],
) -> _ClassifiedHistoryFiles:
    inventory_tree_ts = _compute_timestamp_from_tree_path(inventory_tree)
    archive_file_paths_by_ts = {
        ts: fp for fp in archive_file_paths if (ts := _compute_timestamp_from_archive_file_name(fp))
    }

    delta_cache_from_inventory_tree: Path | None = None
    delta_cache_files_by_ts = {}
    for file_path in delta_cache_file_paths:
        if (
            delta_cache_timestamps := _compute_timestamps_from_delta_cache_file_name(file_path)
        ) is None:
            continue

        previous_timestamp, current_timestamp = delta_cache_timestamps
        if current_timestamp == inventory_tree_ts:
            delta_cache_from_inventory_tree = file_path
        else:
            delta_cache_files_by_ts[(previous_timestamp, current_timestamp)] = _File(
                path=file_path, timestamp=current_timestamp
            )

    sorted_archive_ts = sorted(archive_file_paths_by_ts)
    bundles: dict[tuple[int, int], _File | _ArchiveBundle] = {
        (previous_timestamp, current_timestamp): _ArchiveBundle(
            previous=archive_file_paths_by_ts[previous_timestamp],
            current=archive_file_paths_by_ts[current_timestamp],
            delta_cache=delta_cache_files_by_ts.pop((previous_timestamp, current_timestamp), None),
            timestamp=current_timestamp,
        )
        for previous_timestamp, current_timestamp in zip(sorted_archive_ts, sorted_archive_ts[1:])
    }
    bundles.update({k: f for k, f in delta_cache_files_by_ts.items() if k not in bundles})

    handled_ts = {ts for p_ts, c_ts in bundles for ts in (p_ts, c_ts)}
    return _ClassifiedHistoryFiles(
        delta_cache_from_inventory_tree=delta_cache_from_inventory_tree,
        bundles=list(bundles.values()),
        single_archive_files=[
            _File(path=fp, timestamp=ts)
            for ts, fp in archive_file_paths_by_ts.items()
            if ts not in handled_ts
        ],
    )


def _cleanup_bundle(bundle: _File | _ArchiveBundle, logger: logging.Logger) -> None:
    match bundle:
        case _File():
            logger.warning("Remove single delta cache file %(path)r", {"path": bundle.path})
            bundle.path.unlink(missing_ok=True)
        case _ArchiveBundle():
            logger.warning("Remove archive file %(path)r", {"path": bundle.previous})
            # We never remove the current path because it may belong to the previous bundle
            bundle.previous.unlink(missing_ok=True)
            if bundle.delta_cache is not None:
                logger.warning(
                    "Remove delta cache file of bundle %(path)r", {"path": bundle.delta_cache.path}
                )
                bundle.delta_cache.path.unlink(missing_ok=True)


def _cleanup_abandoned_files_of_host(
    abandoned_files_of_host: _AbandonedFilesOfHost, logger: logging.Logger
) -> None:
    for folder, files in abandoned_files_of_host.folders_and_files.items():
        for file in files:
            logger.warning("Remove abandoned host file %(path)r", {"path": file.path})
            file.path.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            # Folder not empty
            folder.rmdir()

    for file in abandoned_files_of_host.files:
        logger.warning("Remove abandoned host file %(path)r", {"path": file.path})
        file.path.unlink(missing_ok=True)


class InventoryCleanup:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def run(
        self,
        cleanup_parameters: InvCleanupParams,
        *,
        host_names: Sequence[HostName],
        now: int,
        logger: logging.Logger,
    ) -> None:
        hosts_params = cleanup_parameters["for_hosts"]
        default_params = cleanup_parameters["default"]
        abandoned_params = _ParamsFileAge(cleanup_parameters["abandoned_file_age"])

        classified_file_paths = _compute_classified_file_paths(self.inv_paths, host_names)

        for host_name, file_paths in classified_file_paths.by_host.items():
            if (params := _compute_host_params(hosts_params, default_params, host_name)) is None:
                continue

            classified_history_files = _compute_classified_history_files(
                inventory_tree=file_paths.inventory_tree,
                archive_file_paths=file_paths.archive_file_paths,
                delta_cache_file_paths=file_paths.delta_cache_file_paths,
            )

            if classified_history_files.delta_cache_from_inventory_tree is not None:
                classified_history_files.delta_cache_from_inventory_tree.unlink(missing_ok=True)

            for bundle in params.compute_removable_bundles(now, classified_history_files.bundles):
                _cleanup_bundle(bundle, logger)

            for archive_file in classified_history_files.single_archive_files:
                if params.file_is_too_old(now, archive_file.timestamp):
                    logger.warning(
                        "Remove too old archive file %(path)r", {"path": archive_file.path}
                    )
                    archive_file.path.unlink(missing_ok=True)

        for abandoned_files_of_host in classified_file_paths.abandoned_host_files:
            if (
                timestamp := abandoned_files_of_host.compute_youngest_timestamp()
            ) is not None and abandoned_params.file_is_too_old(now, timestamp):
                _cleanup_abandoned_files_of_host(abandoned_files_of_host, logger)

        for file in classified_file_paths.abandoned_files:
            if abandoned_params.file_is_too_old(now, file.timestamp):
                logger.warning("Remove abandoned file %(path)r", {"path": file.path})
                file.path.unlink(missing_ok=True)
