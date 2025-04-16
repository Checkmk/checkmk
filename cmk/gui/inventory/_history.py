#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.structured_data import (
    HistoryEntry,
    HistoryPath,
    ImmutableDeltaTree,
    load_history,
    TreeOrArchiveStore,
)

from cmk.gui.i18n import _

from ._tree import get_permitted_inventory_paths, make_filter_choices_from_permitted_paths


def load_latest_delta_tree(hostname: HostName) -> ImmutableDeltaTree:
    if "/" in hostname:
        return ImmutableDeltaTree()

    filter_tree = (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := get_permitted_inventory_paths(), list)
        else None
    )
    history = load_history(
        TreeOrArchiveStore(
            cmk.utils.paths.inventory_output_dir,
            cmk.utils.paths.inventory_archive_dir,
        ),
        Path(cmk.utils.paths.inventory_delta_cache_dir),
        hostname,
        filter_history_paths=lambda pairs: [pairs[-1]] if pairs else [],
        filter_tree=filter_tree,
    )
    return history.entries[0].delta_tree if history.entries else ImmutableDeltaTree()


def _sort_corrupted_history_files(corrupted_history_files: Sequence[Path]) -> Sequence[str]:
    return sorted(
        [str(fp.relative_to(cmk.utils.paths.omd_root)) for fp in set(corrupted_history_files)]
    )


def load_delta_tree(hostname: HostName, timestamp: int) -> tuple[ImmutableDeltaTree, Sequence[str]]:
    """Load inventory history and compute delta tree of a specific timestamp"""
    if "/" in hostname:
        return ImmutableDeltaTree(), []  # just for security reasons

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
    history = load_history(
        TreeOrArchiveStore(
            cmk.utils.paths.inventory_output_dir,
            cmk.utils.paths.inventory_archive_dir,
        ),
        Path(cmk.utils.paths.inventory_delta_cache_dir),
        hostname,
        filter_history_paths=lambda pairs: _search_timestamps(pairs, timestamp),
        filter_tree=filter_tree,
    )
    return (
        history.entries[0].delta_tree if history.entries else ImmutableDeltaTree(),
        _sort_corrupted_history_files(history.corrupted),
    )


def get_history(hostname: HostName) -> tuple[Sequence[HistoryEntry], Sequence[str]]:
    if "/" in hostname:
        return [], []  # just for security reasons

    filter_tree = (
        make_filter_choices_from_permitted_paths(permitted_paths)
        if isinstance(permitted_paths := get_permitted_inventory_paths(), list)
        else None
    )
    history = load_history(
        TreeOrArchiveStore(
            cmk.utils.paths.inventory_output_dir,
            cmk.utils.paths.inventory_archive_dir,
        ),
        Path(cmk.utils.paths.inventory_delta_cache_dir),
        hostname,
        filter_history_paths=lambda pairs: pairs,
        filter_tree=filter_tree,
    )
    return history.entries, _sort_corrupted_history_files(history.corrupted)
