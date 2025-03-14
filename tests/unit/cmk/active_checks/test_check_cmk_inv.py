#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Sequence

import pytest

from cmk.active_checks.check_cmk_inv import parse_arguments


@pytest.mark.parametrize(
    "argv,expected_args",
    [
        (
            ["test_host"],
            argparse.Namespace(
                hostname="test_host",
                inv_fail_status=1,
                hw_changes=0,
                sw_changes=0,
                sw_missing=0,
                nw_changes=0,
            ),
        ),
        (
            [
                "test_host",
                "--inv-fail-status=2",
                "--hw-changes=1",
                "--sw-changes=1",
                "--sw-missing=1",
                "--nw-changes=1",
            ],
            argparse.Namespace(
                hostname="test_host",
                inv_fail_status=2,
                hw_changes=1,
                sw_changes=1,
                sw_missing=1,
                nw_changes=1,
            ),
        ),
    ],
)
def test_parse_arguments(argv: Sequence[str], expected_args: Sequence[str]) -> None:
    assert parse_arguments(argv) == expected_args
