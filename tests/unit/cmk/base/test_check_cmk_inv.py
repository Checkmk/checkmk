#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Sequence

import pytest

from cmk.base.check_cmk_inv import parse_arguments


@pytest.mark.parametrize(
    "argv,expected_args",
    [
        (
            ["test_host"],
            argparse.Namespace(
                hostname="test_host",
                use_indexed_plugins=False,
                inv_fail_status=1,
                hw_changes=0,
                sw_changes=0,
                sw_missing=0,
                nw_changes=0,
                new_labels=1,
                vanished_labels=0,
                changed_labels=1,
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
                use_indexed_plugins=False,
                inv_fail_status=2,
                hw_changes=1,
                sw_changes=1,
                sw_missing=1,
                nw_changes=1,
                new_labels=1,
                vanished_labels=0,
                changed_labels=1,
            ),
        ),
        (
            [
                "test_host",
                "--use-indexed-plugins",
                "--inv-fail-status=2",
                "--hw-changes=1",
                "--sw-changes=1",
                "--sw-missing=1",
                "--nw-changes=1",
                "--new-labels=2",
                "--vanished-labels=1",
                "--changed-labels=3",
            ],
            argparse.Namespace(
                hostname="test_host",
                use_indexed_plugins=True,
                inv_fail_status=2,
                hw_changes=1,
                sw_changes=1,
                sw_missing=1,
                nw_changes=1,
                new_labels=2,
                vanished_labels=1,
                changed_labels=3,
            ),
        ),
    ],
)
def test_parse_arguments(argv: Sequence[str], expected_args: Sequence[str]) -> None:
    assert parse_arguments(argv) == expected_args


@pytest.mark.parametrize(
    "option",
    [
        "--inv-fail-status",
        "--hw-changes",
        "--sw-changes",
        "--sw-missing",
        "--nw-changes",
        "--new-labels",
        "--vanished-labels",
        "--changed-labels",
    ],
)
def test_parse_arguments_rejects_a_state_out_of_range(option: str) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(["test_host", f"{option}=4"])
