#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import copy
import itertools
import shutil
import struct
import uuid
from functools import lru_cache
from typing import Any, Dict

import pytest

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.crash_reporting import _format_var_for_export, ABCCrashReport, CrashReportStore


class UnitTestCrashReport(ABCCrashReport):
    @classmethod
    def type(cls):
        return "test"


@pytest.fixture()
def crash():
    try:
        raise ValueError("XYZ")
    except ValueError:
        return UnitTestCrashReport.from_exception()


def test_crash_report_type(crash) -> None:
    assert crash.type() == "test"


def test_crash_report_ident(crash) -> None:
    assert crash.ident() == (crash.crash_info["id"],)


def test_crash_report_ident_to_text(crash) -> None:
    assert crash.ident_to_text() == crash.crash_info["id"]


def test_crash_report_crash_dir(crash) -> None:
    assert crash.crash_dir() == (cmk.utils.paths.crash_dir / crash.type() / crash.ident_to_text())


def test_crash_report_local_crash_report_url(crash) -> None:
    url = "crash.py?component=test&ident=%s" % crash.ident_to_text()
    assert crash.local_crash_report_url() == url


def test_format_var_for_export_strip_nested_dict() -> None:
    orig_var: Dict[str, Any] = {
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
    orig_var: Dict[str, Any] = {
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
def crash_dir():
    d = cmk.utils.paths.crash_dir / "test"
    yield d
    try:
        shutil.rmtree(str(d))
    except OSError:
        pass


@pytest.fixture
def patch_uuid1(monkeypatch):
    """Generate a uuid1 with known values."""
    c = itertools.count()

    def uuid1(node=None, clock_seq=None):
        return uuid.UUID(bytes=struct.pack(b">I", next(c)) + 12 * b"\0")

    monkeypatch.setattr("uuid.uuid1", uuid1)


@pytest.fixture
def cache_general_version_infos(monkeypatch):
    """Cache the computation to save time for repeated crash report creation"""

    monkeypatch.setattr(
        cmk_version, "get_general_version_infos", lru_cache(cmk_version.get_general_version_infos)
    )


@pytest.mark.usefixtures("patch_uuid1", "cache_general_version_infos")
@pytest.mark.parametrize("n_crashes", [15, 45])
def test_crash_report_store_cleanup(crash_dir, n_crashes) -> None:
    store = CrashReportStore()
    assert not set(crash_dir.glob("*"))

    crash_ids = []

    for num in range(n_crashes):
        try:
            raise ValueError("Crash #%d" % num)
        except ValueError:
            crash = UnitTestCrashReport.from_exception()
            store.save(crash)
            crash_ids.append(crash.ident_to_text())

    assert len(set(crash_dir.glob("*"))) <= store._keep_num_crashes
    assert {e.name for e in crash_dir.glob("*")} == set(crash_ids[-store._keep_num_crashes :])
