#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

from cmk.ccc import store
from cmk.crash import CrashReportStore

_TRACEBACK = [("mymodule.py", 42, "my_func", "raise ValueError('x')")]
_TRACEBACK_B = [("other.py", 7, "other_func", "raise RuntimeError('y')")]


def _crashes_dir(tmp_path: Path, crash_type: str = "check") -> Path:
    d = tmp_path / "var/check_mk/crashes" / crash_type
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_crash(
    crashes_dir: Path,
    name: str,
    time: object,
    traceback: list[tuple[str, int, str, str]] | None = _TRACEBACK,
    exc_type: str = "ValueError",
    crash_info_version: int | None = None,
) -> Path:
    crash_dir = crashes_dir / name
    crash_dir.mkdir()
    info: dict[str, object] = {
        "crash_type": "check",
        "exc_type": exc_type,
        "exc_value": "x",
        "exc_traceback": traceback,
        "local_vars": "",
        "details": {},
        "id": name,
        "core": "cmc",
        "python_version": "3.12",
        "edition": "cce",
        "python_paths": [],
        "version": "2.5.0",
        "os": "Linux",
        "time": time,
    }
    if crash_info_version is not None:
        info["crash_info_version"] = crash_info_version
    store.save_text_to_file(crash_dir / "crash.info", json.dumps(info))
    return crash_dir


# ---------------------------------------------------------------------------
# No-traceback crashes
# ---------------------------------------------------------------------------


def test_migrate_no_traceback_legacy_time_is_written(tmp_path: Path) -> None:
    """A no-traceback crash with a legacy float time must be rewritten in dict format."""
    crashes_dir = _crashes_dir(tmp_path)
    crash_dir = _write_crash(crashes_dir, "crash-a", time=1000.0, traceback=None)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    info = json.loads(store.load_text_from_file(crash_dir / "crash.info"))
    assert info["time"] == {"first_seen": 1000.0, "last_seen": 1000.0, "count": 1}


def test_migrate_no_traceback_already_migrated_is_not_rewritten(tmp_path: Path) -> None:
    """A no-traceback crash already in dict format with version must not be touched."""
    crashes_dir = _crashes_dir(tmp_path)
    already_migrated = {"first_seen": 500.0, "last_seen": 500.0, "count": 1}
    crash_dir = _write_crash(
        crashes_dir, "crash-a", time=already_migrated, traceback=None, crash_info_version=1
    )
    mtime_before = (crash_dir / "crash.info").stat().st_mtime_ns

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    assert (crash_dir / "crash.info").stat().st_mtime_ns == mtime_before


# ---------------------------------------------------------------------------
# Single-group crashes (unique fingerprint, one crash on disk)
# ---------------------------------------------------------------------------


def test_migrate_single_crash_legacy_time_is_written(tmp_path: Path) -> None:
    """A single crash with a legacy float time must be rewritten in dict format."""
    crashes_dir = _crashes_dir(tmp_path)
    crash_dir = _write_crash(crashes_dir, "crash-a", time=2000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    info = json.loads(store.load_text_from_file(crash_dir / "crash.info"))
    assert info["time"] == {"first_seen": 2000.0, "last_seen": 2000.0, "count": 1}


def test_migrate_single_crash_already_migrated_is_not_rewritten(tmp_path: Path) -> None:
    """A single crash already in dict format with version must not be touched."""
    crashes_dir = _crashes_dir(tmp_path)
    already_migrated = {"first_seen": 1000.0, "last_seen": 2000.0, "count": 3}
    crash_dir = _write_crash(crashes_dir, "crash-a", time=already_migrated, crash_info_version=1)
    mtime_before = (crash_dir / "crash.info").stat().st_mtime_ns

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    assert (crash_dir / "crash.info").stat().st_mtime_ns == mtime_before


# ---------------------------------------------------------------------------
# Multi-crash merging
# ---------------------------------------------------------------------------


def test_migrate_merges_duplicate_crashes(tmp_path: Path) -> None:
    """Multiple crashes sharing a fingerprint are merged into one directory."""
    crashes_dir = _crashes_dir(tmp_path)
    _write_crash(crashes_dir, "crash-1000", time=1000.0)
    _write_crash(crashes_dir, "crash-2000", time=2000.0)
    _write_crash(crashes_dir, "crash-3000", time=3000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    dirs = [p for p in crashes_dir.iterdir() if p.is_dir()]
    assert len(dirs) == 1
    info = json.loads(store.load_text_from_file(dirs[0] / "crash.info"))
    assert info["time"] == {"first_seen": 1000.0, "last_seen": 3000.0, "count": 3}


def test_migrate_keeps_directory_with_latest_last_seen(tmp_path: Path) -> None:
    """The surviving directory must be the one with the highest last_seen timestamp."""
    crashes_dir = _crashes_dir(tmp_path)
    _write_crash(crashes_dir, "crash-early", time=1000.0)
    _write_crash(crashes_dir, "crash-late", time=9000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    dirs = [p for p in crashes_dir.iterdir() if p.is_dir()]
    assert len(dirs) == 1
    assert dirs[0].name == "crash-late"


def test_migrate_removes_duplicate_directories(tmp_path: Path) -> None:
    """Directories discarded during merging must be deleted from disk."""
    crashes_dir = _crashes_dir(tmp_path)
    _write_crash(crashes_dir, "crash-old", time=1000.0)
    _write_crash(crashes_dir, "crash-new", time=2000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    assert not (crashes_dir / "crash-old").exists()


def test_migrate_does_not_merge_different_fingerprints(tmp_path: Path) -> None:
    """Crashes with different fingerprints must remain as separate directories."""
    crashes_dir = _crashes_dir(tmp_path)
    _write_crash(crashes_dir, "crash-a", time=1000.0, traceback=_TRACEBACK, exc_type="ValueError")
    _write_crash(
        crashes_dir, "crash-b", time=2000.0, traceback=_TRACEBACK_B, exc_type="RuntimeError"
    )

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    dirs = [p for p in crashes_dir.iterdir() if p.is_dir()]
    assert len(dirs) == 2


def test_migrate_merges_legacy_and_new_format(tmp_path: Path) -> None:
    """A legacy float crash and an already-migrated dict crash with the same fingerprint are merged."""
    crashes_dir = _crashes_dir(tmp_path)
    _write_crash(crashes_dir, "crash-legacy", time=1000.0)
    _write_crash(
        crashes_dir, "crash-new", time={"first_seen": 2000.0, "last_seen": 3000.0, "count": 2}
    )

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    dirs = [p for p in crashes_dir.iterdir() if p.is_dir()]
    assert len(dirs) == 1
    info = json.loads(store.load_text_from_file(dirs[0] / "crash.info"))
    assert info["time"] == {"first_seen": 1000.0, "last_seen": 3000.0, "count": 3}


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    """Running the migration twice must produce the same result as running it once."""
    crashes_dir = _crashes_dir(tmp_path)
    _write_crash(crashes_dir, "crash-1000", time=1000.0)
    _write_crash(crashes_dir, "crash-2000", time=2000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)
    dirs_after_first = {p.name for p in crashes_dir.iterdir() if p.is_dir()}
    info_after_first = json.loads(
        store.load_text_from_file(crashes_dir / next(iter(dirs_after_first)) / "crash.info")
    )

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)
    dirs_after_second = {p.name for p in crashes_dir.iterdir() if p.is_dir()}
    info_after_second = json.loads(
        store.load_text_from_file(crashes_dir / next(iter(dirs_after_second)) / "crash.info")
    )

    assert dirs_after_first == dirs_after_second
    assert info_after_first["time"] == info_after_second["time"]


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_migrate_skips_unreadable_crash_info(tmp_path: Path) -> None:
    """A crash.info that cannot be parsed must be skipped without aborting the migration."""
    crashes_dir = _crashes_dir(tmp_path)
    bad_dir = crashes_dir / "crash-bad"
    bad_dir.mkdir()
    store.save_text_to_file(bad_dir / "crash.info", "not valid json{{{")

    good_dir = _write_crash(crashes_dir, "crash-good", time=1000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    # The good crash was migrated; the bad directory was left untouched
    info = json.loads(store.load_text_from_file(good_dir / "crash.info"))
    assert info["time"] == {"first_seen": 1000.0, "last_seen": 1000.0, "count": 1}
    assert bad_dir.exists()


def test_migrate_skips_missing_crash_info(tmp_path: Path) -> None:
    """A crash directory without a crash.info file must be silently skipped."""
    crashes_dir = _crashes_dir(tmp_path)
    empty_dir = crashes_dir / "crash-empty"
    empty_dir.mkdir()

    good_dir = _write_crash(crashes_dir, "crash-good", time=1000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    info = json.loads(store.load_text_from_file(good_dir / "crash.info"))
    assert info["time"] == {"first_seen": 1000.0, "last_seen": 1000.0, "count": 1}
    assert empty_dir.exists()


def test_migrate_skips_non_directory_entries(tmp_path: Path) -> None:
    """Non-directory entries (e.g. lock files) in the crash type dir must be ignored."""
    crashes_dir = _crashes_dir(tmp_path)
    (crashes_dir / ".crash_report_lock").touch()
    store.save_text_to_file(crashes_dir / "stray.txt", "noise")

    crash_dir = _write_crash(crashes_dir, "crash-a", time=1000.0)

    CrashReportStore().consolidate_crash_type_dir(crashes_dir)

    info = json.loads(store.load_text_from_file(crash_dir / "crash.info"))
    assert info["time"] == {"first_seen": 1000.0, "last_seen": 1000.0, "count": 1}


def test_migrate_empty_crash_type_dir(tmp_path: Path) -> None:
    """An empty crash-type directory must be handled gracefully."""
    crashes_dir = _crashes_dir(tmp_path)
    CrashReportStore().consolidate_crash_type_dir(crashes_dir)  # must not raise


def test_migrate_processes_multiple_crash_type_dirs(tmp_path: Path) -> None:
    """Migrating two crash-type directories independently produces correct results in each.

    Verifies that time-format migration and deduplication work correctly when
    applied to each crash-type directory in turn, which is what __call__ does.
    """
    check_dir = _crashes_dir(tmp_path, "check")
    _write_crash(check_dir, "check-1000", time=1000.0)
    _write_crash(check_dir, "check-2000", time=2000.0)

    gui_dir = _crashes_dir(tmp_path, "gui")
    _write_crash(gui_dir, "gui-500", time=500.0, exc_type="KeyError")
    _write_crash(gui_dir, "gui-600", time=600.0, exc_type="KeyError")

    CrashReportStore().consolidate_crash_type_dir(check_dir)
    CrashReportStore().consolidate_crash_type_dir(gui_dir)

    check_dirs = [p for p in check_dir.iterdir() if p.is_dir()]
    assert len(check_dirs) == 1
    check_info = json.loads(store.load_text_from_file(check_dirs[0] / "crash.info"))
    assert check_info["time"] == {"first_seen": 1000.0, "last_seen": 2000.0, "count": 2}

    gui_dirs = [p for p in gui_dir.iterdir() if p.is_dir()]
    assert len(gui_dirs) == 1
    gui_info = json.loads(store.load_text_from_file(gui_dirs[0] / "crash.info"))
    assert gui_info["time"] == {"first_seen": 500.0, "last_seen": 600.0, "count": 2}
