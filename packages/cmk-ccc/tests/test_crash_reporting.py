#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

import pytest

from cmk.ccc.crash_reporting import (
    _FINGERPRINT_INDEX_FILE,
    ABCCrashReport,
    crash_fingerprint,
    CrashInfo,
    CrashReportStore,
    fingerprint_hash,
    format_var_for_export,
    make_crash_report_base_path,
    REDACTED_STRING,
    VersionInfo,
)


def test_format_var_for_export_strip_large_data() -> None:
    orig_var = {
        "a": {"y": ("a" * 1024 * 1024) + "a"},
    }

    var = copy.deepcopy(orig_var)
    formated: Any = format_var_for_export(var)

    # Stripped?
    assert formated["a"]["y"].endswith("(1 bytes stripped)")

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_nested_dict_with_list() -> None:
    orig_var: dict[str, object] = {
        "a": {
            "b": {
                "c": [{}],
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated: Any = format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"][0] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_nested_dict() -> None:
    orig_var: dict[str, object] = {
        "a": {
            "b": {
                "c": {
                    "d": {},
                },
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated: Any = format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"]["d"] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


NOT_MODIFIED = object()


@pytest.mark.parametrize(
    "input_,output",
    (
        ("foo", NOT_MODIFIED),
        ({"secret": "secret"}, {"secret": REDACTED_STRING}),
        ({("secret", 1): "secret"}, NOT_MODIFIED),
        (
            ["secret", 1],
            NOT_MODIFIED,
        ),
        (
            ["secret", 1, {"secret": "secret"}],
            ["secret", 1, {"secret": REDACTED_STRING}],
        ),
        ({"secret", 1}, NOT_MODIFIED),
        (
            "this should need truncation because it is longer than 20 chars",
            "this should need tru... (42 bytes stripped)",
        ),
        (frozenset(("secret", 1)), NOT_MODIFIED),
        (
            frozenset(
                ("secret", 1, "this should need truncation because it is longer than 20 chars")
            ),
            frozenset(("secret", 1, "this should need tru... (42 bytes stripped)")),
        ),
    ),
)
def test_format_var_for_export(input_: object, output: object) -> None:
    if output is NOT_MODIFIED:
        output = input_

    assert format_var_for_export(input_, maxsize=20) == output


def test_format_var_for_export_broken_repr() -> None:
    """format_var_for_export must not propagate exceptions from __repr__.

    Regression test for CMK-32623: the crash handler crashed itself when
    pprint.pformat() called repr() on a timeseries object whose __repr__
    raised an exception.
    """

    class BrokenRepr:
        def __repr__(self) -> str:
            raise RuntimeError("repr is broken")

    result = format_var_for_export({"x": BrokenRepr()})
    assert isinstance(result, dict)
    assert "repr raised an exception" in result["x"]


class UnitTestDetails(TypedDict):
    vars: Mapping[str, str]


class UnitTestCrashReport(ABCCrashReport[UnitTestDetails]):
    @classmethod
    def type(cls) -> str:
        return "test"


@pytest.fixture()
def crash(tmp_path: Path) -> UnitTestCrashReport:
    try:
        # We need some var so the local_vars are part of the crash report
        some_local_var = [{"foo": {"deep": True, "password": "verysecret", "foo": "notsecret"}}]
        password = "verysecret"
        raise ValueError(f"XYZ {some_local_var} {password}")  # use local vars to make ruff happy
    except ValueError:
        return UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=0.0,
                    os="Foobuntu",
                ),
                UnitTestDetails(
                    vars={
                        "my_secret": "1234",
                        "not_import": "1234",
                        "auth_token": "1234",
                    }
                ),
            ),
        )


def test_crash_report_type(crash: UnitTestCrashReport) -> None:
    assert crash.type() == "test"


def test_crash_report_sanitization(crash: UnitTestCrashReport) -> None:
    assert crash.crash_info["details"] == UnitTestDetails(
        vars={
            "my_secret": REDACTED_STRING,
            "not_import": "1234",
            "auth_token": REDACTED_STRING,
        }
    )


def test_crash_report_sanitization_local_vars(crash: UnitTestCrashReport) -> None:
    decoded_local_vars = base64.b64decode(crash.crash_info["local_vars"])
    assert b"verysecret" not in decoded_local_vars
    assert b"notsecret" in decoded_local_vars


def test_crash_report_ident(crash: UnitTestCrashReport) -> None:
    assert crash.ident() == (crash.crash_info["id"],)


def test_crash_report_ident_to_text(crash: UnitTestCrashReport) -> None:
    assert crash.ident_to_text() == crash.crash_info["id"]


def test_crash_report_crash_dir(tmp_path: Path, crash: UnitTestCrashReport) -> None:
    assert (
        crash.crash_dir()
        == tmp_path / "var/check_mk/crashes" / crash.type() / crash.ident_to_text()
    )


def test_crash_report_local_crash_report_url(crash: UnitTestCrashReport) -> None:
    url = "crash.py?component=test&ident=%s" % crash.ident_to_text()
    assert crash.local_crash_report_url() == url


def _make_unique_crash(tmp_path: Path, num: int, timestamp: float = 0.0) -> UnitTestCrashReport:
    """Create a crash with a unique fingerprint by using a distinct exception type per num."""
    UniqueExc: type[Exception] = type(f"UniqueError{num}", (Exception,), {})
    try:
        raise UniqueExc("crash")
    except UniqueExc:
        return UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=timestamp,
                    os="Foobuntu",
                ),
                UnitTestDetails(vars={}),
            ),
        )


@pytest.mark.parametrize("n_crashes", [2, 4, 6])
def test_crash_report_store_cleanup(tmp_path: Path, n_crashes: int) -> None:
    crash_store = CrashReportStore(
        keep_num_crashes=4  # use a sane small number for performance reasons
    )
    crashes = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()
    assert not set(crashes.glob("*"))

    crash_ids = []

    for num in range(n_crashes):
        crash = _make_unique_crash(tmp_path, num)
        crash_store.save(crash)
        crash_ids.append(crash.ident_to_text())

    crash_dirs = {e for e in crashes.glob("*") if e.is_dir()}
    assert len(crash_dirs) <= crash_store.keep_num_crashes
    assert {e.name for e in crash_dirs} == set(crash_ids[-crash_store.keep_num_crashes :])


def test_crash_report_store_ignores_non_directories_in_base_dir(tmp_path: Path) -> None:
    """Saving a crash must not fail when non-directory entries exist in the base dir.

    The lock file and any other stray files must be silently skipped during
    the fingerprint scan in _get_existing_crash.
    """
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()
    crashes_dir.mkdir(parents=True)

    # Place a regular file (simulating the lock file or any stray file) directly in base_dir.
    (crashes_dir / ".crash_report_lock").touch()
    (crashes_dir / "stray_file.txt").write_text("not a crash dir")

    try:
        raise ValueError("some error")
    except ValueError:
        crash = UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=0.0,
                    os="Foobuntu",
                ),
                UnitTestDetails(vars={}),
            ),
        )
        crash_store.save(crash)

    crash_dirs = [p for p in crashes_dir.iterdir() if p.is_dir()]
    assert len(crash_dirs) == 1


def test_crash_report_store_no_deduplication_without_traceback(tmp_path: Path) -> None:
    """Crashes without a traceback must each get their own directory.

    An empty traceback produces a degenerate fingerprint that would incorrectly
    merge unrelated crashes, so deduplication is skipped in that case.
    """
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()

    for ts in [1000.0, 2000.0]:
        crash = UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=ts,
                    os="Foobuntu",
                ),
                UnitTestDetails(vars={}),
            ),
        )
        # Remove the traceback to simulate a crash with no traceback information.
        crash.crash_info.pop("exc_traceback", None)
        crash_store.save(crash)

    assert len([p for p in crashes_dir.glob("*") if p.is_dir()]) == 2


def test_crash_report_store_deduplication(tmp_path: Path) -> None:
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()

    # Save the same crash three times with different timestamps
    timestamps = [1000.0, 2000.0, 3000.0]
    crash_ids = []
    for ts in timestamps:
        try:
            raise ValueError("same error")
        except ValueError:
            crash = UnitTestCrashReport(
                crash_report_base_path=make_crash_report_base_path(tmp_path),
                crash_info=UnitTestCrashReport.make_crash_info(
                    VersionInfo(
                        core="test",
                        python_version="test",
                        edition="test",
                        python_paths=["foo", "bar"],
                        version="3.99",
                        time=ts,
                        os="Foobuntu",
                    ),
                    UnitTestDetails(vars={}),
                ),
            )
            crash_store.save(crash)
            crash_ids.append(crash.ident_to_text())

    # All three occurrences share the same fingerprint — only one directory on disk
    on_disk = [p for p in crashes_dir.glob("*") if p.is_dir()]
    assert len(on_disk) == 1

    # The first crash's directory is kept; subsequent saves merge into it.
    # After save() merges a crash, the crash object's ID must be updated to the
    # first-occurrence UUID so callers get a link/ID that resolves to an existing report.
    assert crash_ids[0] == crash_ids[1] == crash_ids[2] == on_disk[0].name

    crash_info = json.loads((on_disk[0] / "crash.info").read_text())
    assert crash_info["crash_info_version"] == 1
    assert crash_info["time"] == {
        "first_seen": timestamps[0],
        "last_seen": timestamps[-1],
        "count": len(timestamps),
    }


def test_crash_report_store_deduplication_out_of_order(tmp_path: Path) -> None:
    """Crashes arriving out of order must not corrupt first_seen / last_seen.

    When an older crash (lower timestamp) arrives after a newer one has already
    been stored, first_seen must be set to the minimum and last_seen to the
    maximum of all observed timestamps regardless of arrival order.
    """
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()

    # Arrive in reverse chronological order: newest first, then oldest
    timestamps_arrival_order = [3000.0, 1000.0]
    for ts in timestamps_arrival_order:
        try:
            raise ValueError("same error")
        except ValueError:
            crash = UnitTestCrashReport(
                crash_report_base_path=make_crash_report_base_path(tmp_path),
                crash_info=UnitTestCrashReport.make_crash_info(
                    VersionInfo(
                        core="test",
                        python_version="test",
                        edition="test",
                        python_paths=["foo", "bar"],
                        version="3.99",
                        time=ts,
                        os="Foobuntu",
                    ),
                    UnitTestDetails(vars={}),
                ),
            )
            crash_store.save(crash)

    on_disk = [p for p in crashes_dir.glob("*") if p.is_dir()]
    assert len(on_disk) == 1

    crash_info = json.loads((on_disk[0] / "crash.info").read_text())
    assert crash_info["crash_info_version"] == 1
    assert crash_info["time"] == {
        "first_seen": 1000.0,
        "last_seen": 3000.0,
        "count": 2,
    }


def test_crash_report_store_corrupted_crash_info_saves_new_crash(tmp_path: Path) -> None:
    """A corrupted crash.info on disk must not prevent saving a new crash.

    When _get_existing_crash encounters a crash.info that cannot be read or
    parsed, it must skip that directory and fall through to creating a fresh
    crash report instead of propagating the exception.
    """
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()
    crashes_dir.mkdir(parents=True)

    # Plant a directory with a corrupted crash.info to simulate on-disk corruption
    bad_dir = crashes_dir / "corrupted-crash"
    bad_dir.mkdir()
    (bad_dir / "crash.info").write_text("not valid json{{{")

    try:
        raise ValueError("new error")
    except ValueError:
        crash = UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=1000.0,
                    os="Foobuntu",
                ),
                UnitTestDetails(vars={}),
            ),
        )
        crash_store.save(crash)  # must not raise

    new_dirs = [p for p in crashes_dir.iterdir() if p.is_dir() and p != bad_dir]
    assert len(new_dirs) == 1
    saved_info = json.loads((new_dirs[0] / "crash.info").read_text())
    assert saved_info["crash_info_version"] == 1
    assert saved_info["time"]["count"] == 1


def test_crash_report_store_missing_crash_info_saves_new_crash(tmp_path: Path) -> None:
    """A crash directory whose crash.info is absent must not prevent saving a new crash."""
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()
    crashes_dir.mkdir(parents=True)

    # Directory exists but has no crash.info
    (crashes_dir / "empty-crash-dir").mkdir()

    try:
        raise ValueError("new error")
    except ValueError:
        crash = UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=1000.0,
                    os="Foobuntu",
                ),
                UnitTestDetails(vars={}),
            ),
        )
        crash_store.save(crash)  # must not raise

    new_dirs = [p for p in crashes_dir.iterdir() if p.is_dir() and p.name != "empty-crash-dir"]
    assert len(new_dirs) == 1


@pytest.mark.parametrize(
    "crash_info, different_result",
    [
        pytest.param(
            {
                "details": {
                    "section": {
                        ("foo", "bar"): {
                            "id": "1337",
                            "name": "foobar",
                        },
                    },
                },
            },
            {
                "details": {
                    "section": {
                        '["foo", "bar"]': {
                            "id": "1337",
                            "name": "foobar",
                        },
                    },
                },
            },
            id="crash_info with tuple as dict key",
        ),
        pytest.param(
            {
                "details": {
                    "section": {
                        '["foo", "bar"]': {
                            "id": "1337",
                            "name": "foobar",
                        },
                    },
                },
            },
            None,
            id="crash_info with list as str as dict key",
        ),
        pytest.param(
            {"foo": "bar"},
            None,
            id="default",
        ),
    ],
)
def test_crash_report_json_dump(
    # TODO: The CrashInfo types and the values passed to them are a lie! Fix this!
    crash_info: CrashInfo[dict[str, object]],
    different_result: CrashInfo[dict[str, object]] | None,
) -> None:
    if different_result:
        assert json.loads(CrashReportStore.dump_crash_info(crash_info)) == different_result
        return
    assert json.loads(CrashReportStore.dump_crash_info(crash_info)) == crash_info


def test_fingerprint_hash_is_stable() -> None:
    """The same fingerprint must always produce the same hash."""
    fp = ("check", "ValueError", (("mymodule.py", 42), ("other.py", 7)))
    assert fingerprint_hash(fp) == fingerprint_hash(fp)


def test_fingerprint_hash_differs_for_different_fingerprints() -> None:
    frames = (("mymodule.py", 42),)
    assert fingerprint_hash(("check", "ValueError", frames)) != fingerprint_hash(
        ("check", "TypeError", frames)
    )
    assert fingerprint_hash(("check", "ValueError", frames)) != fingerprint_hash(
        ("gui", "ValueError", frames)
    )
    assert fingerprint_hash(("check", "ValueError", frames)) != fingerprint_hash(
        ("check", "ValueError", (("mymodule.py", 99),))
    )


def test_fingerprint_hash_handles_none_exc_type() -> None:
    frames = (("mymodule.py", 1),)
    assert fingerprint_hash(("check", None, frames)) != fingerprint_hash(
        ("check", "ValueError", frames)
    )


def test_crash_report_store_writes_fingerprint_index(tmp_path: Path) -> None:
    """Saving a crash with a traceback must create the fingerprint index file."""
    crash_store = CrashReportStore()
    crashes_dir = tmp_path / "var/check_mk/crashes" / UnitTestCrashReport.type()

    try:
        raise ValueError("indexing test")
    except ValueError:
        crash = UnitTestCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=[],
                    version="3.99",
                    time=0.0,
                    os="Foobuntu",
                ),
                UnitTestDetails(vars={}),
            ),
        )
        crash_store.save(crash)

    index_path = crashes_dir / _FINGERPRINT_INDEX_FILE
    assert index_path.exists()

    index = json.loads(index_path.read_text())
    fp = crash_fingerprint(
        crash_type=crash.crash_info["crash_type"],
        exc_traceback=crash.crash_info["exc_traceback"],
        exc_type=crash.crash_info["exc_type"],
    )
    expected_hash = fingerprint_hash(fp)
    assert expected_hash in index
    assert index[expected_hash] == crash.ident_to_text()


def test_fingerprint_hash_returns_hex_string() -> None:
    fp = ("check", "ValueError", (("mymodule.py", 1),))
    result = fingerprint_hash(fp)
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 hex digest
    int(result, 16)  # raises if not valid hex
