#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import marshal
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cmk.profiling.backend import (
    DEFAULT_MAX_PROFILES,
    delete_all_profiles,
    delete_profile,
    enforce_retention,
    get_metadata,
    get_profile_path,
    list_metadata,
    new_profile_id,
    PROFILE_ID_RE,
    PROFILE_SUFFIXES,
    ProfileMetadata,
    write_profile,
)


def _fake_profile_bytes() -> bytes:
    return marshal.dumps({("/tmp/x.py", 1, "f"): (1, 1, 0.01, 0.02, {})})


@pytest.fixture(name="store_dir")
def _store_dir(tmp_path: Path) -> Path:
    return tmp_path / "profiles"


def test_new_profile_id_shape() -> None:
    pid, _now = new_profile_id()
    assert PROFILE_ID_RE.match(pid), pid


def test_profile_id_re_rejects_path_traversal() -> None:
    for bad in ["..", "../", "20260420_123456_abcd", "x" * 50, ""]:
        assert PROFILE_ID_RE.match(bad) is None


def test_profile_id_re_accepts_12_hex() -> None:
    assert PROFILE_ID_RE.match("20260420_123456_0123456789ab")


def test_write_and_read_roundtrip(store_dir: Path) -> None:
    pid = write_profile(
        store_dir,
        profile_bytes=_fake_profile_bytes(),
        source_type="gui_request",
        source_info="GET /foo",
        duration_ms=12.5,
    )
    meta = get_metadata(store_dir, pid)
    assert meta is not None
    assert meta.profile_id == pid
    assert meta.source_type == "gui_request"
    assert meta.source_info == "GET /foo"
    assert meta.duration_ms == 12.5

    profile_path = get_profile_path(store_dir, pid)
    assert profile_path is not None
    assert profile_path.read_bytes() == _fake_profile_bytes()


def test_list_sorted_newest_first(store_dir: Path) -> None:
    ids = [
        write_profile(
            store_dir,
            profile_bytes=_fake_profile_bytes(),
            source_type="gui_request",
            source_info=f"req {i}",
            duration_ms=None,
        )
        for i in range(3)
    ]
    listed = [m.profile_id for m in list_metadata(store_dir)]
    # Newest first → reverse-chronological matches reverse of insertion order,
    # assuming the uuid suffixes keep them distinct within the same second.
    assert set(listed) == set(ids)


def test_list_skips_corrupt_metadata(store_dir: Path) -> None:
    pid = write_profile(
        store_dir,
        profile_bytes=_fake_profile_bytes(),
        source_type="gui_request",
        source_info="ok",
        duration_ms=None,
    )
    bad_id = "20260420_120000_deadbeef1234"
    (store_dir / f"{bad_id}.json").write_text("not json")
    listed = [m.profile_id for m in list_metadata(store_dir)]
    assert pid in listed
    assert bad_id not in listed


def test_get_metadata_rejects_bad_id(store_dir: Path) -> None:
    store_dir.mkdir()
    assert get_metadata(store_dir, "../etc/passwd") is None


def test_get_profile_path_rejects_bad_id(store_dir: Path) -> None:
    store_dir.mkdir()
    assert get_profile_path(store_dir, "../evil") is None


def test_delete_profile_removes_both_files(store_dir: Path) -> None:
    pid = write_profile(
        store_dir,
        profile_bytes=_fake_profile_bytes(),
        source_type="gui_request",
        source_info="x",
        duration_ms=None,
    )
    assert delete_profile(store_dir, pid) is True
    for suffix in PROFILE_SUFFIXES:
        assert not (store_dir / f"{pid}{suffix}").exists()


def test_delete_profile_rejects_bad_id(store_dir: Path) -> None:
    assert delete_profile(store_dir, "../bad") is False


def test_delete_all_removes_orphans(store_dir: Path) -> None:
    store_dir.mkdir()
    # One well-formed pair
    write_profile(
        store_dir,
        profile_bytes=_fake_profile_bytes(),
        source_type="gui_request",
        source_info="a",
        duration_ms=None,
    )
    # An orphan .profile without sidecar
    orphan_id = "20260420_120000_cafebabe1234"
    (store_dir / f"{orphan_id}.profile").write_bytes(b"x")
    assert delete_all_profiles(store_dir) >= 1
    assert list(store_dir.iterdir()) == []


def test_delete_all_skips_foreign_json(store_dir: Path) -> None:
    store_dir.mkdir()
    (store_dir / "notes.json").write_text("{}", encoding="utf-8")
    (store_dir / "notes.profile").write_bytes(b"keep me")
    assert delete_all_profiles(store_dir) == 0
    assert (store_dir / "notes.json").is_file()
    assert (store_dir / "notes.profile").is_file()


def test_enforce_retention_max_count(store_dir: Path) -> None:
    for _ in range(5):
        write_profile(
            store_dir,
            profile_bytes=_fake_profile_bytes(),
            source_type="gui_request",
            source_info="x",
            duration_ms=None,
        )
    removed = enforce_retention(store_dir, max_count=3)
    assert removed == 2
    assert len(list_metadata(store_dir)) == 3


def test_enforce_retention_max_age(store_dir: Path) -> None:
    store_dir.mkdir()
    # Write one "old" metadata directly with a stale timestamp
    old_id = "20260101_000000_aabbccdd0011"
    (store_dir / f"{old_id}.profile").write_bytes(b"x")
    (store_dir / f"{old_id}.json").write_text(
        json.dumps(
            {
                "profile_id": old_id,
                "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
                "source_type": "gui_request",
                "source_info": "old",
                "duration_ms": None,
            }
        )
    )
    # Write a fresh one
    fresh = write_profile(
        store_dir,
        profile_bytes=_fake_profile_bytes(),
        source_type="gui_request",
        source_info="fresh",
        duration_ms=None,
    )

    removed = enforce_retention(store_dir, max_count=100, max_age_days=5)
    assert removed == 1
    remaining = [m.profile_id for m in list_metadata(store_dir)]
    assert remaining == [fresh]


def test_enforce_retention_age_zero_is_ignored(store_dir: Path) -> None:
    """max_age_days<=0 must not wipe the store — guards against malformed config."""
    for _ in range(3):
        write_profile(
            store_dir,
            profile_bytes=_fake_profile_bytes(),
            source_type="gui_request",
            source_info="x",
            duration_ms=None,
        )
    enforce_retention(store_dir, max_count=100, max_age_days=0)
    assert len(list_metadata(store_dir)) == 3


def test_enforce_retention_reaps_orphan_profiles(store_dir: Path) -> None:
    write_profile(
        store_dir,
        profile_bytes=_fake_profile_bytes(),
        source_type="gui_request",
        source_info="ok",
        duration_ms=None,
    )
    orphan = "20260420_120000_deadbeef5678"
    (store_dir / f"{orphan}.profile").write_bytes(b"x")
    enforce_retention(store_dir)
    assert not (store_dir / f"{orphan}.profile").exists()


def test_enforce_retention_noop_when_missing_dir(tmp_path: Path) -> None:
    assert enforce_retention(tmp_path / "nope") == 0


def test_default_max_profiles_is_exported() -> None:
    assert DEFAULT_MAX_PROFILES == 100


def test_profile_metadata_from_json(store_dir: Path) -> None:
    store_dir.mkdir()
    pid = "20260420_120000_1234abcd5678"
    path = store_dir / f"{pid}.json"
    path.write_text(
        json.dumps(
            {
                "profile_id": pid,
                "timestamp": "2026-04-20T12:00:00",
                "source_type": "file_upload",
                "source_info": "upload.prof",
                "duration_ms": None,
            }
        )
    )
    meta = ProfileMetadata.from_json(path)
    assert meta.source_type == "file_upload"
    assert meta.duration_ms is None
