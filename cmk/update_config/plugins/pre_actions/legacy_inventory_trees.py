#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Sequence
from functools import partial
from logging import Logger
from pathlib import Path
from typing import override, Protocol

from cmk.ccc import store
from cmk.ccc.version import Version
from cmk.inventory.paths import Paths as InventoryPaths
from cmk.inventory.transformation import TransformationResultsStore
from cmk.update_config.lib import ExpiryVersion, format_warning
from cmk.update_config.plugins.pre_actions.utils import ConflictMode
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.paths import omd_root
from cmk.utils.render import approx_age

_HIDDEN_FILE_PREFIX = "."
_JSON_SUFFIX = ".json"
_JSON_GZ_SUFFIX = ".json.gz"
_FIRST_RELEASE_WITH_THE_TRANSFORMATION = (2, 5)


class ListFileNames(Protocol):
    def __call__(self, directory: Path, /) -> Sequence[str]: ...


class LoadTransformationResults(Protocol):
    def __call__(self) -> object: ...


class ReadFromVersion(Protocol):
    def __call__(self) -> str | None: ...


def _is_update_from_before_the_transformation(raw_from_version: str | None) -> bool:
    if raw_from_version is None:
        return False
    try:
        base = Version.from_str(raw_from_version.rsplit(".", 1)[0]).base
    except ValueError:
        return False
    return base is not None and (base.major, base.minor) < _FIRST_RELEASE_WITH_THE_TRANSFORMATION


def _list_file_names(directory: Path) -> Sequence[str]:
    try:
        return os.listdir(directory)
    except (FileNotFoundError, NotADirectoryError):
        return []


def _is_legacy_tree_file_name(name: str) -> bool:
    return not name.startswith(_HIDDEN_FILE_PREFIX) and not name.endswith(
        (_JSON_SUFFIX, _JSON_GZ_SUFFIX)
    )


def _count_legacy_tree_files(directory: Path, list_file_names: ListFileNames) -> int:
    return sum(1 for name in list_file_names(directory) if _is_legacy_tree_file_name(name))


def _count_legacy_history_tree_files(directory: Path, list_file_names: ListFileNames) -> int:
    return sum(
        _count_legacy_tree_files(directory / host_dir_name, list_file_names)
        for host_dir_name in list_file_names(directory)
    )


def _count_legacy_trees(inventory_paths: InventoryPaths, list_file_names: ListFileNames) -> int:
    return (
        _count_legacy_tree_files(inventory_paths.inventory_dir, list_file_names)
        + _count_legacy_tree_files(inventory_paths.status_data_dir, list_file_names)
        + _count_legacy_history_tree_files(inventory_paths.archive_dir, list_file_names)
        + _count_legacy_history_tree_files(inventory_paths.delta_cache_dir, list_file_names)
    )


def _parse_duration(raw_result: object) -> float | None:
    if not isinstance(raw_result, dict):
        return None
    match raw_result.get("duration"):
        case float() as duration:
            return duration
        case _:
            return None


def _parse_durations(raw_results: object) -> Sequence[float]:
    if not isinstance(raw_results, list):
        return []
    return [d for r in raw_results if (d := _parse_duration(r)) is not None]


def _render_estimate(durations: Sequence[float], legacy_tree_count: int) -> str:
    if not durations:
        return ""
    average = sum(durations) / len(durations)
    return (
        f" Measured on {len(durations)} converted trees, converting the remaining ones"
        f" takes about {approx_age(average * legacy_tree_count)}."
    )


def _render_warning(durations: Sequence[float], legacy_tree_count: int) -> str:
    return (
        f"HW/SW Inventory: {legacy_tree_count} trees still use the legacy file format.\n"
        "Checkmk 3.0 reads only trees in the new file format. Convert all trees before"
        " updating to it.\n"
        "A nightly job converts 1/200 of all trees per run."
        f"{_render_estimate(durations, legacy_tree_count)}\n"
        "To convert them now, for example outside business hours, run as site user:\n"
        f"  cmk-transform-inventory-trees --bundle-length {legacy_tree_count}\n"
        "To see the progress and the trees of hosts that no longer exist, run:\n"
        "  cmk-transform-inventory-trees --show-results\n"
        "Trees of hosts that no longer exist are not converted; delete the files listed there."
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
        list_file_names: ListFileNames,
        load_transformation_results: LoadTransformationResults,
        read_from_version: ReadFromVersion,
    ) -> None:
        super().__init__(
            name=name, title=title, sort_index=sort_index, expiry_version=expiry_version
        )
        self._inventory_paths = inventory_paths
        self._list_file_names = list_file_names
        self._load_transformation_results = load_transformation_results
        self._read_from_version = read_from_version

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        if _is_update_from_before_the_transformation(self._read_from_version()):
            return
        if legacy_tree_count := _count_legacy_trees(self._inventory_paths, self._list_file_names):
            logger.warning(
                format_warning(
                    _render_warning(
                        _parse_durations(self._load_transformation_results()), legacy_tree_count
                    )
                )
            )


pre_update_action_registry.register(
    LegacyInventoryTrees(
        name="legacy_inventory_trees",
        title="Check for HW/SW Inventory trees in the legacy file format",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_260,
        inventory_paths=InventoryPaths(omd_root),
        list_file_names=_list_file_names,
        load_transformation_results=partial(
            store.load_object_from_file, TransformationResultsStore(omd_root).file_path, default=[]
        ),
        read_from_version=partial(os.environ.get, "OMD_FROM_VERSION"),
    )
)
