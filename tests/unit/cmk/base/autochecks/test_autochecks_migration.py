#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
from pathlib import Path
from typing import Sequence

import pytest

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName

from cmk.base.autochecks.migration import load_unmigrated_autocheck_entries
from cmk.base.autochecks.utils import AutocheckEntry


def test_load_unmigrated_autocheck_entries_with_check_var(tmp_path: Path) -> None:

    with (tmp_path / "file").open("w") as file_:
        file_.write(
            """[
  {'check_plugin_name': 'norris', 'item': None, 'parameters': chuck, 'service_labels': {}},
]
"""
        )

    assert load_unmigrated_autocheck_entries(tmp_path / "file", {"chuck": {}}) == [
        AutocheckEntry(
            check_plugin_name=CheckPluginName("norris"),
            item=None,
            parameters={},
            service_labels={},
        ),
    ]

    with pytest.raises(MKGeneralException):
        _ = load_unmigrated_autocheck_entries(tmp_path / "file", {})


@pytest.mark.parametrize(
    "autochecks_content",
    [
        "@",
        "[abc123]",
        "[{'check_plugin_name': 123, 'item': 'abc', 'parameters': {}, 'service_labels': {}}]\n",
    ],
)
def test_load_unmigrated_autocheck_entries_raises(
    tmp_path: Path,
    autochecks_content: str,
) -> None:
    with (tmp_path / "file").open("w") as f:
        f.write(autochecks_content)

    with pytest.raises(MKGeneralException):
        _ = load_unmigrated_autocheck_entries(tmp_path / "file", {})


def test_load_unmigrated_autocheck_entries_not_existing() -> None:
    assert load_unmigrated_autocheck_entries(Path("/no/such/file"), {}) == []


@pytest.mark.parametrize(
    "autochecks_content,expected_result",
    [
        ("[]", []),
        ("", []),
        # Tuple: Regular processing
        (
            "[\n    ('df', '/', {}),\n]\n",
            [
                AutocheckEntry(
                    CheckPluginName("df"),
                    "/",
                    {},
                    {},
                ),
            ],
        ),
        # Dict: fix legacy subcheck
        (
            """[
  {'check_plugin_name': 'sub.check', 'item': None, 'parameters': {}, 'service_labels': {}},
]""",
            [
                AutocheckEntry(
                    CheckPluginName("sub_check"),
                    None,
                    {},
                    {},
                ),
            ],
        ),
        # Dict: Allow non string items
        (
            """[
  {'check_plugin_name': 'df', 'item': 123, 'parameters': {}, 'service_labels': {}},
]""",
            [
                AutocheckEntry(
                    CheckPluginName("df"),
                    "123",
                    {},
                    {},
                ),
            ],
        ),
        # Dict: Regular processing
        (
            """[
  {'check_plugin_name': 'cpu_loads', 'item': None, 'parameters': {}, 'service_labels': {}},
  {'check_plugin_name': 'lnx_if', 'item': '2', 'parameters': {'state': ['1']}, 'service_labels': {}},
]""",
            [
                AutocheckEntry(CheckPluginName("cpu_loads"), None, {}, {}),
                AutocheckEntry(
                    CheckPluginName("lnx_if"),
                    "2",
                    {"state": ["1"]},
                    {},
                ),
            ],
        ),
    ],
)
def test_load_unmigrated_autocheck_entries(
    tmp_path: Path,
    autochecks_content: str,
    expected_result: Sequence[AutocheckEntry],
) -> None:
    with (tmp_path / "file").open("w") as f:
        f.write(autochecks_content)

    assert load_unmigrated_autocheck_entries(tmp_path / "file", {}) == expected_result
