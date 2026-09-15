#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.base.base_app import CheckmkBaseApp
from cmk.base.community_app import make_app
from cmk.base.modes.call import call
from cmk.base.modes.modes import (
    Dispatch,
    Mode,
    NoArgument,
    Option,
    OptionalArguments,
    RequiredArgument,
    SubOptions,
    SubOptionsAndOptionalArguments,
    SubOptionsAndRequiredArgument,
)
from cmk.trace import Context

_APP: Final = make_app()

_SUB_OPTIONS: Final = [Option(long_option="flag", short_help="a flag")]


def _mode(dispatch: Dispatch) -> Mode:
    return Mode(long_option="test-mode", dispatch=dispatch, short_help="a mode under test")


def _call(mode: Mode, argument: str = "", *, arguments: Sequence[str] = ()) -> int:
    return call(_APP, mode, argument, [("--flag", "")], arguments, Context())


def test_a_mode_without_arguments_returns_its_handlers_exit_code() -> None:
    assert _call(_mode(NoArgument(handler=lambda _app: 23))) == 23


def test_a_required_argument_reaches_the_handler() -> None:
    received: list[str] = []

    def handler(_app: CheckmkBaseApp, argument: str) -> int:
        received.append(argument)
        return 0

    _call(_mode(RequiredArgument(descr="HOST", handler=handler)), "myhost")

    assert received == ["myhost"]


def test_the_positional_arguments_reach_the_handler() -> None:
    received: list[Sequence[str]] = []

    def handler(_app: CheckmkBaseApp, arguments: Sequence[str]) -> int:
        received.append(arguments)
        return 0

    _call(_mode(OptionalArguments(descr="HOSTS", handler=handler)), arguments=["host1", "host2"])

    assert received == [["host1", "host2"]]


def test_the_sub_options_reach_the_handler() -> None:
    received: list[Mapping[str, object]] = []

    def handler(_app: CheckmkBaseApp, parsed: Mapping[str, object]) -> int:
        received.append(parsed)
        return 0

    _call(_mode(SubOptions(options=_SUB_OPTIONS, handler=handler)))

    assert received == [{"flag": True}]


def test_the_sub_options_and_a_required_argument_reach_the_handler() -> None:
    received: list[tuple[Mapping[str, object], str]] = []

    def handler(_app: CheckmkBaseApp, parsed: Mapping[str, object], argument: str) -> int:
        received.append((parsed, argument))
        return 0

    _call(
        _mode(SubOptionsAndRequiredArgument(options=_SUB_OPTIONS, descr="HOST", handler=handler)),
        "myhost",
    )

    assert received == [({"flag": True}, "myhost")]


def test_the_sub_options_and_the_positional_arguments_reach_the_handler() -> None:
    received: list[tuple[Mapping[str, object], Sequence[str]]] = []

    def handler(
        _app: CheckmkBaseApp, parsed: Mapping[str, object], arguments: Sequence[str]
    ) -> int:
        received.append((parsed, arguments))
        return 0

    _call(
        _mode(SubOptionsAndOptionalArguments(options=_SUB_OPTIONS, descr="HOSTS", handler=handler)),
        arguments=["host1"],
    )

    assert received == [({"flag": True}, ["host1"])]
