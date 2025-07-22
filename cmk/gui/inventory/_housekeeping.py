#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import subprocess
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.gui.config import Config
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.valuespec import Age, Dictionary, Integer, ListOf, TextOrRegExp
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement
from cmk.inventory.config import (
    InvHousekeepingParamsFallback,
    InvHousekeepingParamsOfHosts,
    matches,
)
from cmk.utils.structured_data import InventoryPaths, TreePath


def _vs_file_age() -> Age:
    return Age(
        title=_("Remove inventory files which are older than"),
        minvalue=1,
    )


def _vs_number_of_history_entries() -> Integer:
    return Integer(
        title=_("Remove history entries right after the"),
        default_value=50,
        unit=_("th entry"),
        minvalue=1,
    )


ConfigVariableInventoryHousekeeping = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    domain=ConfigDomainGUI,
    ident="inventory_housekeeping",
    valuespec=lambda: Dictionary(
        title=_("Cleanup HW/SW Inventory files"),
        elements=[
            (
                "of_hosts",
                ListOf(
                    Dictionary(
                        elements=[
                            (
                                "regexes_or_names",
                                ListOf(
                                    TextOrRegExp(),
                                    title=_("Restrict to host names"),
                                    magic="!@#",
                                    allow_empty=False,
                                ),
                            ),
                            ("file_age", _vs_file_age()),
                            ("number_of_history_entries", _vs_number_of_history_entries()),
                        ],
                        optional_keys=["file_age", "number_of_history_entries"],
                    ),
                    title=_("For specific hosts"),
                ),
            ),
            (
                "fallback",
                Dictionary(
                    title=_("Fallback"),
                    elements=[
                        ("file_age", _vs_file_age()),
                        ("number_of_history_entries", _vs_number_of_history_entries()),
                    ],
                    optional_keys=["file_age"],
                ),
            ),
        ],
        optional_keys=[],
    ),
)


def _collect_all_raw_host_names(*, is_wato_slave_site: bool) -> Sequence[str]:
    command = (
        ["check_mk", "--list-hosts", "--include-offline"]
        if is_wato_slave_site
        else ["check_mk", "--list-hosts", "--all-sites", "--include-offline"]
    )
    try:
        return list(set(subprocess.check_output(command, encoding="utf-8").splitlines()))
    except subprocess.CalledProcessError:
        return []


class _FilePathsManager:
    def __init__(
        self,
        *,
        inventory_file_paths: Sequence[Path],
        status_data_file_paths: Sequence[Path],
        archive_file_paths: Sequence[Path],
        delta_cache_file_paths: Sequence[Path],
    ) -> None:
        self._inventory_file_paths = inventory_file_paths
        self._status_data_file_paths = status_data_file_paths
        self._archive_file_paths = archive_file_paths
        self._delta_cache_file_paths = delta_cache_file_paths
        self._handled_file_paths: set[Path] = set()

    def add_handled_tree_paths(self, tree_paths: Sequence[TreePath]) -> None:
        for tree_path in tree_paths:
            self._handled_file_paths.add(tree_path.path)
            self._handled_file_paths.add(tree_path.legacy)

    def add_handled_file_paths(self, file_paths: Sequence[Path]) -> None:
        self._handled_file_paths.update(file_paths)

    def get_unhandled_files(self) -> Sequence[Path]:
        return list(
            (
                set(self._inventory_file_paths)
                .union(self._status_data_file_paths)
                .union(self._archive_file_paths)
                .union(self._delta_cache_file_paths)
            ).difference(self._handled_file_paths)
        )


@dataclass(frozen=True)
class _InvHousekeepingParams:
    now: int
    file_age: int | None
    number_of_history_entries: int | None


def _compute_params_of_host(
    now: int,
    hosts_params: Sequence[InvHousekeepingParamsOfHosts],
    fallback_params: InvHousekeepingParamsFallback,
    host_name: HostName,
) -> _InvHousekeepingParams:
    for host_params in hosts_params:
        for regex_or_name in host_params["regexes_or_names"]:
            if matches(regex_or_name=regex_or_name, host_name=host_name):
                return _InvHousekeepingParams(
                    now=now,
                    file_age=(
                        fallback_params.get("file_age")
                        if (p := host_params.get("file_age")) is None
                        else p
                    ),
                    number_of_history_entries=(
                        fallback_params["number_of_history_entries"]
                        if (p := host_params.get("number_of_history_entries")) is None
                        else p
                    ),
                )
    return _InvHousekeepingParams(
        now=now,
        file_age=fallback_params.get("file_age"),
        number_of_history_entries=fallback_params["number_of_history_entries"],
    )


def _compute_timestamp_from_file_path(file_path: Path) -> int | None:
    try:
        return int(file_path.stat().st_mtime)
    except FileNotFoundError:
        return None


def _compute_timestamp_from_tree_path(tree_path: TreePath) -> int | None:
    if (ts := _compute_timestamp_from_file_path(tree_path.path)) is not None:
        return ts
    return _compute_timestamp_from_file_path(tree_path.legacy)


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


@dataclass(frozen=True, kw_only=True)
class _ClassifiedHistoryFiles:
    delta_cache_from_inventory_tree: _File | None
    bundles: Sequence[_File | _ArchiveBundle]
    single_archive_files: Sequence[_File]

    def iter_file_paths(self) -> Iterator[Path]:
        if self.delta_cache_from_inventory_tree:
            yield self.delta_cache_from_inventory_tree.path
        for bundle in self.bundles:
            match bundle:
                case _File():
                    yield bundle.path
                case _ArchiveBundle():
                    yield bundle.previous
                    yield bundle.current
                    if bundle.delta_cache:
                        yield bundle.delta_cache.path
        for archive_file in self.single_archive_files:
            yield archive_file.path


def _compute_classified_history_files(
    *,
    inventory_tree_ts: int | None,
    archive_file_paths: Sequence[Path],
    delta_cache_file_paths: Sequence[Path],
) -> _ClassifiedHistoryFiles:
    archive_file_paths_by_ts = {int(fp.with_suffix("").name): fp for fp in archive_file_paths}

    delta_cache_from_inventory_tree: _File | None = None
    delta_cache_files_by_ts = {}
    for file_path in delta_cache_file_paths:
        previous_name, current_name = file_path.with_suffix("").name.split("_")
        previous_timestamp = -1 if previous_name == "None" else int(previous_name)
        current_timestamp = int(current_name)
        delta_cache = _File(path=file_path, timestamp=current_timestamp)

        if current_timestamp == inventory_tree_ts:
            delta_cache_from_inventory_tree = delta_cache
        else:
            delta_cache_files_by_ts[(previous_timestamp, current_timestamp)] = delta_cache

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

    handled_ts = set(ts for p_ts, c_ts in bundles for ts in (p_ts, c_ts))
    return _ClassifiedHistoryFiles(
        delta_cache_from_inventory_tree=delta_cache_from_inventory_tree,
        bundles=list(bundles.values()),
        single_archive_files=[
            _File(path=fp, timestamp=ts)
            for ts, fp in archive_file_paths_by_ts.items()
            if ts not in handled_ts
        ],
    )


def _file_is_too_old(now: int, file_age: int, timestamp: int) -> bool:
    return timestamp is not None and now - file_age > timestamp


def _cleanup_bundle(bundle: _File | _ArchiveBundle) -> None:
    match bundle:
        case _File():
            logger.warning("Remove inventory history entry %r", bundle.path)
            bundle.path.unlink(missing_ok=True)
        case _ArchiveBundle():
            logger.warning("Remove inventory history entry %r", bundle.previous)
            # We never remove the current path because it may belong to the previous bundle
            bundle.previous.unlink(missing_ok=True)
            if bundle.delta_cache is not None:
                logger.warning("Remove inventory history entry %r", bundle.delta_cache.path)
                bundle.delta_cache.path.unlink(missing_ok=True)


def _cleanup_history_files(
    now: int,
    params: _InvHousekeepingParams,
    classified_history_files: _ClassifiedHistoryFiles,
) -> None:
    # remove delta cache computed from inventory tree
    if classified_history_files.delta_cache_from_inventory_tree is not None:
        classified_history_files.delta_cache_from_inventory_tree.path.unlink(missing_ok=True)

    descending_bundles = sorted(
        classified_history_files.bundles,
        key=lambda b: b.timestamp,
        reverse=True,
    )
    if params.number_of_history_entries is not None:
        logger.warning(
            "Remove inventory history entries right after the %sth entry",
            params.number_of_history_entries,
        )
        for bundle in descending_bundles[params.number_of_history_entries :]:
            _cleanup_bundle(bundle)
        descending_bundles = descending_bundles[: params.number_of_history_entries]

    if (file_age := params.file_age) is not None:
        for bundle in descending_bundles:
            if _file_is_too_old(now, file_age, bundle.timestamp):
                logger.warning("Remove too old inventory history entry")
                _cleanup_bundle(bundle)

        for archive_file in classified_history_files.single_archive_files:
            if _file_is_too_old(now, file_age, archive_file.timestamp):
                logger.warning("Remove too old archive tree %r", archive_file.path)
                archive_file.path.unlink(missing_ok=True)


class InventoryHousekeeping:
    def __init__(self, omd_root: Path) -> None:
        super().__init__()
        self.inv_paths = InventoryPaths(omd_root)

    def _run(self, config: Config, *, host_names: Sequence[HostName], now: int) -> None:
        hosts_params = config.inventory_housekeeping["of_hosts"]
        fallback_params = config.inventory_housekeeping["fallback"]

        manager = _FilePathsManager(
            inventory_file_paths=list(self.inv_paths.inventory_dir.glob("[!.]*")),
            status_data_file_paths=list(self.inv_paths.status_data_dir.glob("*")),
            archive_file_paths=list(self.inv_paths.archive_dir.glob("*/*")),
            delta_cache_file_paths=list(self.inv_paths.delta_cache_dir.glob("*/*")),
        )

        for host_name in host_names:
            params = _compute_params_of_host(now, hosts_params, fallback_params, host_name)

            inventory_tree = self.inv_paths.inventory_tree(host_name)
            inventory_tree_gz = self.inv_paths.inventory_tree(host_name)
            status_data_tree = self.inv_paths.status_data_tree(host_name)

            inventory_tree_ts = _compute_timestamp_from_tree_path(inventory_tree)
            classified_history_files = _compute_classified_history_files(
                inventory_tree_ts=inventory_tree_ts,
                archive_file_paths=list(self.inv_paths.archive_host(host_name).glob("*")),
                delta_cache_file_paths=list(self.inv_paths.delta_cache_host(host_name).glob("*")),
            )

            manager.add_handled_tree_paths([inventory_tree, inventory_tree_gz, status_data_tree])
            manager.add_handled_file_paths(list(classified_history_files.iter_file_paths()))

            if (file_age := params.file_age) is not None:
                if inventory_tree_ts is not None and _file_is_too_old(
                    now, file_age, inventory_tree_ts
                ):
                    logger.warning("Remove too old inventory tree file %r", inventory_tree.path)
                    logger.warning("Remove too old inventory tree file %r", inventory_tree.legacy)
                    logger.warning("Remove too old inventory tree file %r", inventory_tree_gz.path)
                    logger.warning(
                        "Remove too old inventory tree file %r", inventory_tree_gz.legacy
                    )
                    inventory_tree.path.unlink(missing_ok=True)
                    inventory_tree.legacy.unlink(missing_ok=True)
                    inventory_tree_gz.path.unlink(missing_ok=True)
                    inventory_tree_gz.legacy.unlink(missing_ok=True)

                if (
                    status_data_tree_ts := _compute_timestamp_from_tree_path(status_data_tree)
                ) is not None and _file_is_too_old(now, file_age, status_data_tree_ts):
                    logger.warning("Remove too old status data tree file %r", status_data_tree.path)
                    logger.warning(
                        "Remove too old status data tree file %r", status_data_tree.legacy
                    )
                    status_data_tree.path.unlink(missing_ok=True)
                    status_data_tree.legacy.unlink(missing_ok=True)

            _cleanup_history_files(now, params, classified_history_files)

        if host_names:
            for file_path in manager.get_unhandled_files():
                logger.warning("Remove unhandled inventory file %r", file_path)
                file_path.unlink(missing_ok=True)

    def __call__(self, config: Config) -> None:
        self._run(
            config,
            host_names=[
                HostName(h)
                for h in _collect_all_raw_host_names(
                    is_wato_slave_site=is_wato_slave_site(config.sites)
                )
            ],
            now=int(time.time()),
        )
