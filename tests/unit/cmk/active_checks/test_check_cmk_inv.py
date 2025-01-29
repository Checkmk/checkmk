#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

import pytest
from pytest import CaptureFixture, MonkeyPatch

from cmk.active_checks.check_cmk_inv import get_command, main, parse_arguments


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


def test_get_command() -> None:
    args = argparse.Namespace(
        hostname="test_host",
        inv_fail_status=2,
        hw_changes=1,
        sw_changes=1,
        sw_missing=1,
        nw_changes=1,
    )

    assert get_command(args) == [
        "cmk",
        "--inv-fail-status=2",
        "--hw-changes=1",
        "--sw-changes=1",
        "--sw-missing=1",
        "--nw-changes=1",
        "--inventory-as-check",
        "test_host",
    ]


@dataclass(frozen=True)
class CompletedProcessMock:
    returncode: int
    stdout: str | None
    stderr: str | None


def test_main(monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    mock = CompletedProcessMock(
        returncode=2,
        stdout="Found 107 inventory entries, software changes(!!), Found 50 status entries",
        stderr=None,
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock)

    assert main(["--sw-changes=2", "test_host"]) == 2

    out, err = capsys.readouterr()

    assert out == "Found 107 inventory entries, software changes(!!), Found 50 status entries\n"
    assert err == ""
