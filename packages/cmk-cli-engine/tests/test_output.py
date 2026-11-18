#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
from collections.abc import Iterator, Mapping

import pytest

from cmk.cli.engine.output import Console as CLIConsole

from ._console import FakeRunPager, FakeTerminal


def _console(
    stdout: FakeTerminal,
    run_pager: FakeRunPager | None = None,
    environ: Mapping[str, str] = {},
) -> CLIConsole:
    return CLIConsole(
        stdout=stdout,
        stderr=FakeTerminal(),
        environ=environ,
        run_pager=run_pager or FakeRunPager(),
    )


def _page_on_a_terminal(run_pager: FakeRunPager, environ: Mapping[str, str] = {}) -> FakeTerminal:
    terminal = FakeTerminal(tty=True)
    _console(terminal, run_pager, environ).page("the help\n")
    return terminal


def test_an_error_is_written_to_stderr() -> None:
    stderr = FakeTerminal()

    CLIConsole(
        stdout=FakeTerminal(), stderr=stderr, environ={}, run_pager=FakeRunPager()
    ).write_error("ERROR: it broke\n")

    assert stderr.getvalue() == "ERROR: it broke\n"


def test_a_redirected_help_is_written_as_it_is() -> None:
    stdout = FakeTerminal()

    _console(stdout).page("the help\n")

    assert stdout.getvalue() == "the help\n"


def test_a_help_on_a_terminal_is_shown_by_the_users_pager() -> None:
    run_pager = FakeRunPager()

    _page_on_a_terminal(run_pager, {"PAGER": "most -s"})

    assert run_pager.commands == [["most", "-s"]]


def test_without_a_pager_of_their_own_the_user_gets_less() -> None:
    run_pager = FakeRunPager()

    _page_on_a_terminal(run_pager)

    assert run_pager.commands == [["less"]]


def test_the_pager_is_handed_the_help() -> None:
    run_pager = FakeRunPager()

    _page_on_a_terminal(run_pager)

    assert run_pager.texts == ["the help\n"]


def test_a_help_on_a_terminal_is_not_written_besides_the_pager() -> None:
    assert _page_on_a_terminal(FakeRunPager()).getvalue() == ""


def test_a_missing_pager_falls_back_to_writing_the_help() -> None:
    terminal = _page_on_a_terminal(FakeRunPager(FileNotFoundError("most")))

    assert terminal.getvalue() == "the help\n"


def test_a_pager_that_quits_early_is_no_error() -> None:
    terminal = _page_on_a_terminal(FakeRunPager(BrokenPipeError()))

    assert terminal.getvalue() == ""


def test_a_users_own_less_options_are_kept_after_ours() -> None:
    run_pager = FakeRunPager()

    _page_on_a_terminal(run_pager, {"LESS": "--tabs=4"})

    assert run_pager.environments[0]["LESS"].endswith("$ --tabs=4")


def test_a_page_that_fits_the_screen_is_not_held_open() -> None:
    run_pager = FakeRunPager()

    _page_on_a_terminal(run_pager)

    assert "--quit-if-one-screen" in run_pager.environments[0]["LESS"].split()


@pytest.fixture(name="own_sigint_handler")
def _own_sigint_handler() -> Iterator[None]:
    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


@pytest.mark.usefixtures("own_sigint_handler")
def test_an_interrupt_is_left_to_the_pager() -> None:
    run_pager = FakeRunPager()

    _page_on_a_terminal(run_pager)

    assert run_pager.sigint_handlers == [signal.SIG_IGN]


@pytest.mark.usefixtures("own_sigint_handler")
def test_an_interrupt_is_handled_again_after_paging() -> None:
    _page_on_a_terminal(FakeRunPager())

    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler
