#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
import sys
from collections.abc import Iterator

import pytest

from cmk.ccc.exceptions import MKGeneralException, raise_mkterminate_on_sigint
from cmk.cli.engine.modes import (
    _pager_environment,
    Option,
    option_count,
    option_names,
    option_string,
    option_strings,
    parse_general_options,
    parse_sub_options,
    write_paged,
)
from cmk.cli.internal import GlobalOptions


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
    monkeypatch.setenv("PAGER", "sh -c 'kill -INT $PPID; sleep 1; cat'")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    raise_mkterminate_on_sigint()

    write_paged("the help\n")

    assert capfd.readouterr().out == "the help\n"


def test_a_users_own_less_options_are_kept_after_ours() -> None:
    assert _pager_environment({"LESS": "--tabs=4"})["LESS"].endswith("$ --tabs=4")


def test_an_argument_to_a_flag_option_is_rejected() -> None:
    option = Option(long_option="flag", short_help="a flag")

    with pytest.raises(MKGeneralException):
        parse_sub_options([option], [("--flag", "a value")])


def test_an_option_argument_the_conversion_rejects_is_reported() -> None:
    option = Option(
        long_option="number",
        short_help="a number",
        argument=True,
        argument_descr="N",
        argument_conv=int,
    )

    with pytest.raises(MKGeneralException):
        parse_sub_options([option], [("--number", "not a number")])


def test_a_deprecated_option_warns_about_the_one_it_replaces(
    capsys: pytest.CaptureFixture[str],
) -> None:
    option = Option(
        long_option="plugins", short_help="the plugins", deprecated_long_options={"checks"}
    )

    parse_sub_options([option], [("--checks", "")])

    assert "'plugins'" in capsys.readouterr().out


def test_a_missing_string_option_has_no_value() -> None:
    assert option_string({}, "snmp-backend") is None


def test_a_string_option_that_is_not_a_string_is_rejected() -> None:
    with pytest.raises(MKGeneralException):
        option_string({"snmp-backend": 23}, "snmp-backend")


def test_a_counted_option_that_was_never_given_is_rejected() -> None:
    with pytest.raises(MKGeneralException):
        option_count({}, "discover")


def test_a_name_of_the_wrong_type_is_rejected() -> None:
    with pytest.raises(MKGeneralException):
        option_names({"plugins": {23}}, "plugins", str)


def test_a_missing_collected_option_has_no_values() -> None:
    assert option_strings({}, "oid") == ()


def test_collected_values_that_are_not_strings_are_rejected() -> None:
    with pytest.raises(MKGeneralException):
        option_strings({"oid": (23,)}, "oid")


def test_a_general_flag_is_collected() -> None:
    assert parse_general_options([("--debug", "")]) == GlobalOptions(debug=True)


def test_a_general_option_hands_over_its_argument() -> None:
    assert parse_general_options([("--fake-dns", "1.2.3.4")]) == GlobalOptions(fake_dns="1.2.3.4")


def test_the_verbosity_counts_the_short_and_long_spelling_alike() -> None:
    assert parse_general_options([("-v", ""), ("--verbose", "")]) == GlobalOptions(verbosity=2)


def test_an_option_that_is_not_a_general_one_is_left_alone() -> None:
    assert parse_general_options([("--flag", "")]) == GlobalOptions()
