#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import pytest

from cmk.base.modes.modes import write_paged


def test_a_redirected_help_is_written_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    write_paged("the help\n")

    assert capsys.readouterr().out == "the help\n"


def test_a_help_on_a_terminal_is_written_through_the_pager(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PAGER", "cat")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    write_paged("the help\n")

    assert capfd.readouterr().out == "the help\n"


def test_a_missing_pager_falls_back_to_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PAGER", "no-such-pager-on-this-system")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    write_paged("the help\n")

    assert capsys.readouterr().out == "the help\n"
