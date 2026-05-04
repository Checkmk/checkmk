#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections import defaultdict
from contextlib import suppress
from logging import Logger
from pathlib import Path
from typing import Any, override

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.crash_reporting import (
    crash_fingerprint,
    CRASH_INFO_VERSION,
    CrashInfo,
    CrashOccurrences,
    CrashReportStore,
    make_crash_report_base_path,
    normalize_crash_time,
)
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateCrashReports(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        crashes_base = make_crash_report_base_path(cmk.utils.paths.omd_root)
        if not crashes_base.exists():
            return

        for crash_type_dir in crashes_base.iterdir():
            if not crash_type_dir.is_dir():
                continue
            self._migrate_crash_type_dir(crash_type_dir, logger)

    def _migrate_crash_type_dir(self, crash_type_dir: Path, logger: Logger) -> None:
        groups: dict[
            tuple[str, str | None, tuple[tuple[str, int], ...]],
            list[tuple[Path, CrashInfo[Any], bool]],
        ] = defaultdict(list)
        no_traceback: list[tuple[Path, CrashInfo[Any], bool]] = []

        for crash_dir in crash_type_dir.iterdir():
            if not crash_dir.is_dir():
                continue
            crash_info_path = crash_dir / "crash.info"
            if not crash_info_path.exists():
                continue
            try:
                crash_info: CrashInfo[Any] = json.loads(store.load_text_from_file(crash_info_path))
            except Exception:
                logger.warning("Could not read %s, skipping", crash_info_path)
                continue

            raw_time = crash_info["time"]
            needs_time_migration = not isinstance(raw_time, dict)
            crash_info["time"] = normalize_crash_time(raw_time)

            needs_version_migration = "crash_info_version" not in crash_info
            crash_info["crash_info_version"] = CRASH_INFO_VERSION

            needs_migration = needs_time_migration or needs_version_migration

            exc_traceback = crash_info.get("exc_traceback") or []
            if not exc_traceback:
                no_traceback.append((crash_dir, crash_info, needs_migration))
                continue

            fp = crash_fingerprint(
                crash_type=crash_info["crash_type"],
                exc_traceback=exc_traceback,
                exc_type=crash_info.get("exc_type"),
            )
            groups[fp].append((crash_dir, crash_info, needs_migration))

        # For crashes without traceback, just fix the time/version format
        for crash_dir, crash_info, needs_migration in no_traceback:
            if needs_migration:
                self._write_crash_info(crash_dir / "crash.info", crash_info)
                logger.debug("Migrated crash.info for %s", crash_dir.name)

        # Group and merge crashes with the same fingerprint
        for _fp, group in groups.items():
            if len(group) == 1:
                crash_dir, crash_info, needs_migration = group[0]
                if needs_migration:
                    self._write_crash_info(crash_dir / "crash.info", crash_info)
                    logger.debug("Migrated crash.info for %s", crash_dir.name)
                continue

            merged_first_seen = min(info["time"]["first_seen"] for _, info, _ in group)
            merged_last_seen = max(info["time"]["last_seen"] for _, info, _ in group)
            merged_count = sum(info["time"]["count"] for _, info, _ in group)

            # Keep the crash with the latest last_seen; discard the rest
            group.sort(key=lambda x: x[1]["time"]["last_seen"])
            keep_dir, keep_info, _ = group[-1]
            keep_info["time"] = CrashOccurrences(
                first_seen=merged_first_seen,
                last_seen=merged_last_seen,
                count=merged_count,
            )
            self._write_crash_info(keep_dir / "crash.info", keep_info)
            logger.debug("Merged %d occurrences of crash into %s", merged_count, keep_dir.name)

            for crash_dir, _, _ in group[:-1]:
                for f in crash_dir.iterdir():
                    with suppress(OSError):
                        f.unlink()
                try:
                    crash_dir.rmdir()
                    logger.debug("Removed duplicate crash directory %s", crash_dir.name)
                except OSError:
                    logger.warning(
                        "Could not remove duplicate crash directory %s — "
                        "it will be re-processed on the next migration run",
                        crash_dir.name,
                    )

    @staticmethod
    def _write_crash_info(path: Path, crash_info: CrashInfo[Any]) -> None:
        store.save_text_to_file(path, CrashReportStore.dump_crash_info(crash_info) + "\n")


update_action_registry.register(
    MigrateCrashReports(
        name="migrate_crash_reports",
        title="Crash reports: Migrate to grouped format with occurrence tracking",
        sort_index=150,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
