#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

# pylint: disable=redefined-outer-name
import copy
import itertools
import json
import struct
import uuid
from pathlib import Path
from typing import Any

import pytest

from cmk.ccc.crash_reporting import (
    _format_var_for_export,
    ABCCrashReport,
    CrashInfo,
    CrashReportStore,
    VersionInfo,
)


class UnitTestCrashReport(ABCCrashReport[VersionInfo]):
    @classmethod
    def type(cls):
        return "test"


@pytest.fixture()
def crashdir(tmp_path: Path) -> Path:
    return tmp_path / "crash"


@pytest.fixture()
def crash(crashdir: Path) -> UnitTestCrashReport:
    try:
        raise ValueError("XYZ")
    except ValueError:
        return UnitTestCrashReport(
            crashdir,
            UnitTestCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=0.0,
                    os="Foobuntu",
                ),
            ),
        )


def test_crash_report_type(crash: ABCCrashReport) -> None:
    assert crash.type() == "test"


def test_crash_report_ident(crash: ABCCrashReport) -> None:
    assert crash.ident() == (crash.crash_info["id"],)


def test_crash_report_ident_to_text(crash: ABCCrashReport) -> None:
    assert crash.ident_to_text() == crash.crash_info["id"]


def test_crash_report_crash_dir(crashdir: Path, crash: ABCCrashReport) -> None:
    assert crash.crash_dir() == crashdir / crash.type() / crash.ident_to_text()


def test_crash_report_local_crash_report_url(crash: ABCCrashReport) -> None:
    url = "crash.py?component=test&ident=%s" % crash.ident_to_text()
    assert crash.local_crash_report_url() == url


def test_format_var_for_export_strip_nested_dict() -> None:
    orig_var: dict[str, Any] = {
        "a": {
            "b": {
                "c": {
                    "d": {},
                },
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated = _format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"]["d"] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_large_data() -> None:
    orig_var = {
        "a": {"y": ("a" * 1024 * 1024) + "a"},
    }

    var = copy.deepcopy(orig_var)
    formated = _format_var_for_export(var)

    # Stripped?
    assert formated["a"]["y"].endswith("(1 bytes stripped)")

    # Not modified original data
    assert orig_var == var


def test_format_var_for_export_strip_nested_dict_with_list() -> None:
    orig_var: dict[str, Any] = {
        "a": {
            "b": {
                "c": [{}],
            },
        },
    }

    var = copy.deepcopy(orig_var)
    formated = _format_var_for_export(var)

    # Stripped?
    assert formated["a"]["b"]["c"][0] == "Max recursion depth reached"

    # Not modified original data
    assert orig_var == var


@pytest.fixture
def patch_uuid1(monkeypatch):
    """Generate a uuid1 with known values."""
    c = itertools.count()

    def uuid1(node=None, clock_seq=None):
        return uuid.UUID(bytes=struct.pack(b">I", next(c)) + 12 * b"\0")

    monkeypatch.setattr("uuid.uuid1", uuid1)


@pytest.mark.usefixtures("patch_uuid1")
@pytest.mark.parametrize("n_crashes", [15, 45])
def test_crash_report_store_cleanup(crashdir: Path, n_crashes: int) -> None:
    store = CrashReportStore()
    crashes = crashdir / UnitTestCrashReport.type()
    assert not set(crashes.glob("*"))

    crash_ids = []

    for num in range(n_crashes):
        try:
            raise ValueError("Crash #%d" % num)
        except ValueError:
            crash = UnitTestCrashReport(
                crashdir,
                UnitTestCrashReport.make_crash_info(
                    VersionInfo(
                        core="test",
                        python_version="test",
                        edition="test",
                        python_paths=["foo", "bar"],
                        version="3.99",
                        time=0.0,
                        os="Foobuntu",
                    )
                ),
            )
            store.save(crash)
            crash_ids.append(crash.ident_to_text())

    assert len(set(crashes.glob("*"))) <= store._keep_num_crashes
    assert {e.name for e in crashes.glob("*")} == set(crash_ids[-store._keep_num_crashes :])


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
def test_crash_report_json_dump(crash_info: CrashInfo, different_result: CrashInfo | None) -> None:
    if different_result:
        assert json.loads(CrashReportStore.dump_crash_info(crash_info)) == different_result
        return
    assert json.loads(CrashReportStore.dump_crash_info(crash_info)) == crash_info
