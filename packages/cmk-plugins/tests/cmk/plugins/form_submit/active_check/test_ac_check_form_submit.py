#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Mapping, Sequence

import pytest
import vcr  # type: ignore[import-untyped,unused-ignore]

from cmk.plugins.form_submit.active_check import check_form_submit


@pytest.mark.parametrize(
    "args, expected_exitcode, expected_info",
    [
        (
            [
                "localhost",
                "--uri",
                "/heute",
            ],
            0,
            "Form has been submitted",
        ),
        (
            [
                "localhost",
                "--uri",
                "/heute",
                "--query",
                '"_origtarget=wato.py&_username=cmkadmin&_password=cmk"',
                "--expected_regex",
                "wato",
            ],
            0,
            'Found expected regex "wato" in form response',
        ),
        (
            [
                "localhost",
                "--uri",
                "/heute",
                "--query",
                '"_origtarget=wato.py&_username=cmkadmin&_password=cmk"',
                "--expected_regex",
                "lala",
            ],
            2,
            'Expected regex "lala" could not be found in form response',
        ),
    ],
)
def test_check_form_submit_main(
    args: Sequence[str],
    expected_exitcode: int,
    expected_info: str,
) -> None:
    filepath = "%s/_check_form_submit_response" % os.path.dirname(__file__)
    with vcr.use_cassette(  # type: ignore[no-untyped-call,unused-ignore]
        filepath,
        record_mode="none",
    ):
        exitcode, info = check_form_submit.main(args)
        assert exitcode == expected_exitcode
        assert info == expected_info


@pytest.mark.parametrize(
    "states, expected_status, expected_info",
    [
        ({}, 0, "0 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT")}, 0, "1 succeeded, 0 failed"),
        ({"foo": (1, "SOME_TEXT")}, 1, "0 succeeded, 1 failed (foo: SOME_TEXT)"),
        ({"foo": (2, "SOME_TEXT")}, 2, "0 succeeded, 1 failed (foo: SOME_TEXT)"),
        ({"foo": (0, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2")}, 0, "2 succeeded, 0 failed"),
        (
            {"foo": (1, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2")},
            1,
            "1 succeeded, 1 failed (foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (1, "SOME_TEXT_1"), "bar": (1, "SOME_TEXT_2")},
            1,
            "0 succeeded, 2 failed (bar: SOME_TEXT_2, foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (2, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2")},
            2,
            "1 succeeded, 1 failed (foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (2, "SOME_TEXT_1"), "bar": (1, "SOME_TEXT_2")},
            2,
            "0 succeeded, 2 failed (bar: SOME_TEXT_2, foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (2, "SOME_TEXT_1"), "bar": (2, "SOME_TEXT_2")},
            2,
            "0 succeeded, 2 failed (bar: SOME_TEXT_2, foo: SOME_TEXT_1)",
        ),
        (
            {"foo": (0, "SOME_TEXT_1"), "bar": (0, "SOME_TEXT_2"), "baz": (0, "SOME_TEXT_3")},
            0,
            "3 succeeded, 0 failed",
        ),
    ],
)
def test_ac_check_form_submit_host_states_no_levels(
    states: Mapping[str, tuple[int, str]],
    expected_status: int,
    expected_info: str,
) -> None:
    status, info = check_form_submit.check_host_states(states, None)
    assert status == expected_status
    assert info == expected_info


@pytest.mark.parametrize(
    "states, levels, expected_status, expected_info",
    [
        ({}, None, 0, "0 succeeded, 0 failed"),
        ({}, (0, 0), 2, "0 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT_1")}, None, 0, "1 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT_1")}, (0, 0), 0, "1 succeeded, 0 failed"),
        ({"foo": (0, "SOME_TEXT_1")}, (1, 1), 2, "1 succeeded, 0 failed"),
        ({"foo": (3, "SOME_TEXT_1")}, None, 3, "0 succeeded, 1 failed (foo: SOME_TEXT_1)"),
        ({"foo": (3, "SOME_TEXT_1")}, (0, 0), 2, "0 succeeded, 1 failed (foo: SOME_TEXT_1)"),
        ({"foo": (3, "SOME_TEXT_1")}, (1, 1), 2, "0 succeeded, 1 failed (foo: SOME_TEXT_1)"),
    ],
)
def test_ac_check_form_submit_host_states_levels(
    states: Mapping[str, tuple[int, str]],
    levels: tuple[int, int] | None,
    expected_status: int,
    expected_info: str,
) -> None:
    status, info = check_form_submit.check_host_states(states, levels)
    assert status == expected_status
    assert info == expected_info
