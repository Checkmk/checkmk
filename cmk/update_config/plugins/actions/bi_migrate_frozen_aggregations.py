#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc import store

from cmk.bi.filesystem import get_default_site_filesystem
from cmk.bi.storage import generate_identifier
from cmk.update_config.registry import update_action_registry, UpdateAction

ORIGIN_HINTS_PREFIX = "origin_hints_"


class BIMigrateFrozenAggregations(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        fs = get_default_site_filesystem()
        frozen_aggr_dir = fs.var.frozen_aggregations

        if not any(frozen_aggr_dir.iterdir()):
            logger.info("No frozen aggregations found.")
            return

        if not any(p.name.startswith(ORIGIN_HINTS_PREFIX) for p in frozen_aggr_dir.iterdir()):
            logger.info("Frozen aggregations already migrated.")
            return

        _run_migration(frozen_aggr_dir)
        fs.cache.clear_compilation_cache()


def _run_migration(frozen_aggr_dir: Path) -> None:
    """CMK-22873: migrate from string filenames to nested uuid5 encoded filenames."""
    legacy_origin_hints_info = (
        path
        for path in frozen_aggr_dir.iterdir()
        if path.is_dir() and path.name.startswith(ORIGIN_HINTS_PREFIX)
    )

    for origin_hints_dir in legacy_origin_hints_info:
        for branch_hint in origin_hints_dir.iterdir():
            branch_path = frozen_aggr_dir / branch_hint.name
            target_path = _get_target_path(frozen_aggr_dir, branch_path)

            (branch_path).rename(target_path)
            branch_hint.unlink()

        origin_hints_dir.rmdir()


def _get_target_path(frozen_aggr_dir: Path, branch_path: Path) -> Path:
    aggregation_id, branch_title = _extract_aggregation_id_and_branch_title(branch_path)
    (aggr_dir := (frozen_aggr_dir / generate_identifier(aggregation_id))).mkdir(exist_ok=True)
    return aggr_dir / generate_identifier(branch_title)


def _extract_aggregation_id_and_branch_title(branch_path: Path) -> tuple[str, str]:
    # frozen aggregation id pattern: "frozen_<aggregation_id>_<branch_title>"
    try:
        frozen_aggr_id: str = store.load_object_from_file(branch_path, default={})["id"]
    except KeyError:
        raise SystemError(f"Frozen branch file is not correctly formatted: {branch_path}")

    trimmed_id = frozen_aggr_id.lstrip("frozen_")
    branch_title_idx = trimmed_id.index(branch_path.name)

    aggregation_id = trimmed_id[: branch_title_idx - 1]  # trim trailing underscore
    branch_title = trimmed_id[branch_title_idx:]

    return aggregation_id, branch_title


update_action_registry.register(
    BIMigrateFrozenAggregations(
        name="bi_migrate_frozen_aggregations",
        title="Migrate legacy frozen aggregations.",
        sort_index=2000,
        continue_on_failure=False,
    )
)
