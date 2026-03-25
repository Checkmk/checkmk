#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""On-disk persistence and periodic cleanup of crash reports in the local site.

``CrashReportStore.save()`` preserves the write-time deduplication behavior:
the same lock, the same ``.fingerprint_index``, and the same merge-into-existing
aggregation of ``count`` / ``first_seen`` / ``last_seen`` into the existing
``crash.info``.

``cleanup_crash_reports()`` bounds the crashes directory by count (per type),
age and total size. It is meant to be run regularly, independent of new crashes
arriving."""

import json
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator, Sequence
from contextlib import suppress
from datetime import timedelta
from itertools import islice
from pathlib import Path
from typing import Any, Final

from cmk.ccc import store

from ._crash import (
    ABCCrashReport,
    CRASH_INFO_VERSION,
    CrashInfo,
    CrashOccurrences,
    RobustJSONEncoder,
    TDetails,
)
from ._fingerprint import (
    _drop_from_index,
    _load_fingerprint_index,
    _save_fingerprint_index,
    crash_fingerprint,
    CrashFingerprint,
    normalize_crash_time,
)

_logger = logging.getLogger(__name__)


def _uuid_crash_dirs(type_dir: Path) -> Iterator[Path]:
    """Yield the per-crash directories (named after a UUID) inside a crash-type directory."""
    for p in type_dir.iterdir():
        try:
            uuid.UUID(str(p.name))
        except (ValueError, TypeError):
            continue
        if p.is_dir():
            yield p


def _remove_crash_dir(crash_dir: Path) -> None:
    """Remove a single crash report directory and its contents."""
    for f in crash_dir.iterdir():
        with suppress(OSError):
            f.unlink()
    with suppress(OSError):
        crash_dir.rmdir()


def _crash_dir_last_seen(crash_dir: Path) -> float:
    """Best-effort last-seen timestamp (epoch seconds) for age and ordering decisions.

    Falls back to the directory's modification time when the crash.info is missing or
    unreadable, so a corrupted report is never considered "infinitely new"."""
    try:
        info = json.loads(store.load_text_from_file(crash_dir / "crash.info"))
        return normalize_crash_time(info["time"])["last_seen"]
    except Exception:
        try:
            return crash_dir.stat().st_mtime
        except OSError:
            return 0.0


def _crash_dir_size(crash_dir: Path) -> int:
    """Total size in bytes of the files contained in a crash report directory."""
    total = 0
    for f in crash_dir.iterdir():
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            continue
    return total


DEFAULT_MAX_CRASH_AGE: Final = timedelta(days=90)
DEFAULT_MAX_CRASHES_TOTAL_SIZE: Final = 5 * 1024**3  # 5 GiB


def cleanup_crash_reports(
    base_path: Path,
    *,
    keep_num_crashes: int = 200,
    max_age: timedelta = DEFAULT_MAX_CRASH_AGE,
    max_total_size: int = DEFAULT_MAX_CRASHES_TOTAL_SIZE,
    reference_time: float | None = None,
) -> None:
    """Bound the on-disk crashes directory by count (per type), age and total size.

    Intended to be run regularly (independent of new crashes arriving). Within each crash-type
    directory the newest ``keep_num_crashes`` reports are kept and reports older than ``max_age``
    are removed. Afterwards, if the surviving reports still exceed ``max_total_size`` in sum across
    all types, the oldest ones are evicted until the budget is met."""
    if not base_path.exists():
        return

    ref = time.time() if reference_time is None else reference_time
    age_cutoff = ref - max_age.total_seconds()

    # (last_seen, size, crash_dir, type_dir) of every report that survived the per-type pruning.
    survivors: list[tuple[float, int, Path, Path]] = []

    for type_dir in base_path.iterdir():
        if not type_dir.is_dir():
            continue
        with store.locked(type_dir / ".crash_report_lock"):
            index = _load_fingerprint_index(type_dir)
            crashes = sorted(
                (
                    (_crash_dir_last_seen(p), _crash_dir_size(p), p)
                    for p in _uuid_crash_dirs(type_dir)
                ),
                key=lambda c: c[0],
                reverse=True,  # newest first
            )
            for position, (last_seen, size, crash_dir) in enumerate(crashes):
                if position >= keep_num_crashes or last_seen < age_cutoff:
                    _remove_crash_dir(crash_dir)
                    _drop_from_index(index, crash_dir.name)
                else:
                    survivors.append((last_seen, size, crash_dir, type_dir))
            _save_fingerprint_index(type_dir, index)

    total_size = sum(size for _, size, _, _ in survivors)
    if total_size <= max_total_size:
        return

    for last_seen, size, crash_dir, type_dir in sorted(
        survivors, key=lambda c: c[0]
    ):  # oldest first
        if total_size <= max_total_size:
            break
        with store.locked(type_dir / ".crash_report_lock"):
            index = _load_fingerprint_index(type_dir)
            _remove_crash_dir(crash_dir)
            _drop_from_index(index, crash_dir.name)
            _save_fingerprint_index(type_dir, index)
        total_size -= size


class CrashReportStore:
    """Caring about the persistance of crash reports in the local site"""

    def __init__(self, *, keep_num_crashes: int = 200) -> None:
        self.keep_num_crashes: Final = keep_num_crashes

    def save(self, crash: ABCCrashReport[Any]) -> None:
        """Save the crash report instance to it's crash report directory"""
        base_dir = crash.crash_dir().parent
        base_dir.mkdir(parents=True, exist_ok=True)
        with store.locked(base_dir / ".crash_report_lock"):
            index = _load_fingerprint_index(base_dir)

            if existing_path := self._get_existing_crash(crash, base_dir, index):
                self._merge_into_existing(crash, existing_path)
                _save_fingerprint_index(base_dir, index)
                return

            self._prepare_crash_dump_directory(crash.crash_dir())

            for key, value in crash.serialize().items():
                fname = "crash.info" if key == "crash_info" else key

                if value is None:  # type: ignore[comparison-overlap]
                    continue  # type: ignore[unreachable]

                if fname == "crash.info":
                    store.save_text_to_file(
                        crash.crash_dir() / fname,
                        self.dump_crash_info(value) + "\n",
                    )
                else:
                    assert isinstance(value, bytes)
                    store.save_bytes_to_file(crash.crash_dir() / fname, value)

            exc_traceback = crash.crash_info.get("exc_traceback", [])
            if exc_traceback:
                fp = crash_fingerprint(
                    crash_type=crash.crash_info["crash_type"],
                    exc_traceback=exc_traceback,
                    exc_type=crash.crash_info["exc_type"],
                )
                index[fp.hash()] = crash.crash_dir().name

            self._cleanup_old_crashes(base_dir, index)
            _save_fingerprint_index(base_dir, index)

    def _get_existing_crash(
        self, crash: ABCCrashReport[Any], base_dir: Path, index: dict[str, str]
    ) -> Path | None:
        if not base_dir.exists():
            return None

        exc_traceback = crash.crash_info.get("exc_traceback", [])
        if not exc_traceback:
            return None

        new_fingerprint = crash_fingerprint(
            crash_type=crash.crash_info["crash_type"],
            exc_traceback=exc_traceback,
            exc_type=crash.crash_info["exc_type"],
        )
        fp_hash = new_fingerprint.hash()

        # Fast path: index hit — one directory check instead of N file reads.
        if fp_hash in index:
            candidate = base_dir / index[fp_hash] / "crash.info"
            if candidate.exists():
                return candidate
            # Stale entry (dir was removed externally); fall through to full scan.
            del index[fp_hash]

        # Slow path: full scan. Also rebuilds the index so the next save is fast.
        for existing_dir in base_dir.iterdir():
            if not existing_dir.is_dir():
                continue
            crash_info_path = existing_dir / "crash.info"
            try:
                existing_info = json.loads(store.load_text_from_file(crash_info_path))
            except Exception:
                continue  # missing or corrupted — treat as no match, save new crash

            existing_fp = crash_fingerprint(
                crash_type=existing_info["crash_type"],
                exc_traceback=existing_info.get("exc_traceback", []),
                exc_type=existing_info["exc_type"],
            )
            # Opportunistically populate the index for every entry we read.
            index[existing_fp.hash()] = existing_dir.name

            if existing_fp == new_fingerprint:
                return crash_info_path

        return None

    def _merge_into_existing(self, crash: ABCCrashReport[Any], crash_info_path: Path) -> None:
        existing_info = json.loads(store.load_text_from_file(crash_info_path))
        existing_time = normalize_crash_time(existing_info["time"])
        new_time = crash.crash_info["time"]
        existing_info["time"] = CrashOccurrences(
            first_seen=min(existing_time["first_seen"], new_time["first_seen"]),
            last_seen=max(existing_time["last_seen"], new_time["last_seen"]),
            count=existing_time["count"] + new_time["count"],
        )
        store.save_text_to_file(
            crash_info_path,
            self.dump_crash_info(existing_info) + "\n",
        )
        # Update the in-memory crash ID to the directory that was actually stored
        # (the first-occurrence UUID). All callers that use crash.ident_to_text() after
        # save() will then get a UUID that resolves to an existing crash report.
        crash.crash_info["id"] = crash_info_path.parent.name

    @staticmethod
    def dump_crash_info(crash_info: CrashInfo[TDetails] | bytes) -> str:
        return json.dumps(
            CrashReportStore._dump_crash_info(crash_info),
            cls=RobustJSONEncoder,
            sort_keys=True,
            indent=4,
        )

    @classmethod
    def _dump_crash_info(cls, d: Any) -> Any:
        if not isinstance(d, dict):
            return d
        return {
            k if isinstance(k, str) else json.dumps(k, cls=RobustJSONEncoder): (
                cls._dump_crash_info(v) if isinstance(v, dict) else v
            )
            for k, v in d.items()
        }

    def _prepare_crash_dump_directory(self, crash_dir: Path) -> None:
        crash_dir.mkdir(parents=True, exist_ok=True)

        # Remove all files of former crash reports
        for f in crash_dir.iterdir():
            with suppress(OSError):
                f.unlink()

    def _cleanup_old_crashes(self, base_dir: Path, index: dict[str, str]) -> None:
        """Simple cleanup mechanism: For each crash type we keep up to X crashes"""
        for crash_dir in islice(
            sorted(
                _uuid_crash_dirs(base_dir),
                key=lambda p: uuid.UUID(str(p.name)).time,
                reverse=True,
            ),
            self.keep_num_crashes,
            None,
        ):
            _remove_crash_dir(crash_dir)
            _drop_from_index(index, crash_dir.name)

    def consolidate_all_crash_dirs(self, crashes_base: Path) -> None:
        """Migrate, deduplicate, and prune all crash type directories.

        Called periodically by the background consolidation job to process crash
        reports written by server-side programs that bypass ``CrashReportStore``
        and write files directly (e.g. ``cmk-plugin-apis`` SSP crashes).
        """
        try:
            crash_type_dirs = tuple(crashes_base.iterdir())
        except FileNotFoundError:
            return

        for crash_type_dir in crash_type_dirs:
            if not crash_type_dir.is_dir():
                continue
            try:
                self.consolidate_crash_type_dir(crash_type_dir)
            except Exception:
                _logger.exception("Error consolidating crash dir %s", crash_type_dir.name)

    def consolidate_crash_type_dir(self, crash_type_dir: Path) -> None:
        """Migrate, deduplicate, and prune one crash type directory.

        - Migrates v0 (``time: float``) crash.info files to v1 (``CrashOccurrences``).
        - Merges crash reports that share the same fingerprint.
        - Rebuilds the fingerprint index so subsequent ``save()`` calls take
          the fast index-lookup path.
        - Enforces ``keep_num_crashes`` by removing the oldest surplus entries.
        """
        crash_type_dir.mkdir(parents=True, exist_ok=True)
        with store.locked(crash_type_dir / ".crash_report_lock"):
            groups: dict[CrashFingerprint, list[tuple[Path, CrashInfo[Any], bool]]] = defaultdict(
                list
            )
            # Crashes without a traceback can't be fingerprinted, so they are never
            # merged — only migrated in place to the current on-disk format.
            no_traceback: list[tuple[Path, CrashInfo[Any], bool]] = []

            for crash_dir in crash_type_dir.iterdir():
                if not crash_dir.is_dir():
                    continue
                crash_info_path = crash_dir / "crash.info"
                try:
                    crash_info: CrashInfo[Any] = json.loads(
                        store.load_text_from_file(crash_info_path)
                    )
                except Exception:
                    _logger.debug("Skipping unreadable crash.info in %s", crash_dir.name)
                    continue

                # Bring legacy v0 files up to date: normalize the time field and add the
                # version. ``needs_write`` stays False for already-current files so we
                # don't rewrite them (and bump their mtime) on every consolidation run.
                raw_time = crash_info["time"]
                needs_write = not isinstance(raw_time, dict)
                crash_info["time"] = normalize_crash_time(raw_time)
                if "crash_info_version" not in crash_info:
                    needs_write = True
                crash_info.setdefault("crash_info_version", CRASH_INFO_VERSION)

                exc_traceback = crash_info.get("exc_traceback") or []
                if not exc_traceback:
                    no_traceback.append((crash_dir, crash_info, needs_write))
                    continue

                fp = crash_fingerprint(
                    crash_type=crash_info["crash_type"],
                    exc_traceback=exc_traceback,
                    exc_type=crash_info.get("exc_type"),
                )
                groups[fp].append((crash_dir, crash_info, needs_write))

            for crash_dir, crash_info, needs_write in no_traceback:
                if needs_write:
                    self._write_crash_info(crash_dir / "crash.info", crash_info)

            new_index: dict[str, str] = {}
            for fp, group in groups.items():
                surviving_dir, surviving_info = self._merge_crash_group(
                    [(d, i) for d, i, _ in group]
                )
                # A merged group always changed; a lone crash only if it needed migration.
                if len(group) > 1 or group[0][2]:
                    self._write_crash_info(surviving_dir / "crash.info", surviving_info)
                new_index[fp.hash()] = surviving_dir.name

            self._cleanup_old_crashes(crash_type_dir, new_index)
            _save_fingerprint_index(crash_type_dir, new_index)

    @staticmethod
    def _merge_crash_group[T](
        group: Sequence[tuple[Path, CrashInfo[T]]],
    ) -> tuple[Path, CrashInfo[T]]:
        """Merge all crashes in the group into one, deleting the surplus directories.

        The crash with the most recent ``last_seen`` survives and inherits the
        aggregated occurrences; the rest are removed.
        """
        keep_dir, keep_info = max(group, key=lambda x: x[1]["time"]["last_seen"])
        if len(group) == 1:
            return keep_dir, keep_info

        keep_info["time"] = CrashOccurrences(
            first_seen=min(info["time"]["first_seen"] for _, info in group),
            last_seen=max(info["time"]["last_seen"] for _, info in group),
            count=sum(info["time"]["count"] for _, info in group),
        )

        for crash_dir, _ in group:
            if crash_dir != keep_dir:
                _remove_crash_dir(crash_dir)

        return keep_dir, keep_info

    @staticmethod
    def _write_crash_info(path: Path, crash_info: CrashInfo[Any]) -> None:
        store.save_text_to_file(path, CrashReportStore.dump_crash_info(crash_info) + "\n")
