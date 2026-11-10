#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import sys
from collections.abc import Iterator

import pytest

from cmk.cli.engine.output import _pager_environment as _cli_pager_environment
from cmk.cli.engine.output import write_paged as cli_write_paged
from cmk.cli.engine.output import write_stderr as cli_write_stderr


def test_an_error_is_written_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    cli_write_stderr("ERROR: it broke\n")

    assert capsys.readouterr().err == "ERROR: it broke\n"


def test_a_redirected_help_is_written_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    cli_write_paged("the help\n", {})

    assert capsys.readouterr().out == "the help\n"


def test_a_help_on_a_terminal_is_written_through_the_pager(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    cli_write_paged("the help\n", {"PAGER": "cat"})

    assert capfd.readouterr().out == "the help\n"


def test_a_missing_pager_falls_back_to_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    cli_write_paged("the help\n", {"PAGER": "no-such-pager-on-this-system"})

    assert capsys.readouterr().out == "the help\n"


@pytest.fixture(name="own_sigint_handler")
def _own_sigint_handler() -> Iterator[None]:
    previous = signal.getsignal(signal.SIGINT)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


@pytest.mark.usefixtures("own_sigint_handler")
def test_an_interrupt_leaves_the_pager_to_clean_up_after_itself(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    signal.signal(signal.SIGINT, signal.default_int_handler)

    cli_write_paged("the help\n", {"PAGER": "sh -c 'kill -INT $PPID; sleep 1; cat'"})

    assert capfd.readouterr().out == "the help\n"


def test_a_users_own_less_options_are_kept_after_ours() -> None:
    assert _cli_pager_environment({"LESS": "--tabs=4"})["LESS"].endswith("$ --tabs=4")


def test_a_page_that_fits_the_screen_is_not_held_open() -> None:
    assert "--quit-if-one-screen" in _cli_pager_environment({})["LESS"].split()
