#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        pytest.param(
            (
                "foo",
                "bar",
                ("password", "baz"),
                {"look_for_keys": True},
            ),
            [
                "--host=foo",
                "--user=bar",
                "--secret=baz",
                "--look-for-keys",
            ],
            id="look for keys",
        ),
        pytest.param(
            (
                "foo",
                "bar",
                ("password", "baz"),
                {"look_for_keys": False},
            ),
            [
                "--host=foo",
                "--user=bar",
                "--secret=baz",
            ],
            id="do not look for keys",
        ),
    ],
)
def test_check_sftp_argument_parsing(
    params: tuple[Any],
    expected_args: Sequence[str],
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_sftp")
    assert active_check.run_argument_function(params) == expected_args
