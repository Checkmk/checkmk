#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final

from cmk.base.community_app import make_app
from cmk.cli.engine.call import call
from cmk.cli.engine.modes import Mode, Option
from cmk.cli.internal import Args, CommandHandler, GlobalOptions, Options
from cmk.trace import Context

_APP: Final = make_app()

_GLOBAL_OPTIONS: Final = GlobalOptions(verbosity=2)

_SUB_OPTIONS: Final = [Option(long_option="flag", short_help="a flag")]


class _Recorder:
    def __init__(self, exit_code: int = 0) -> None:
        self.calls: list[tuple[GlobalOptions, Options, Args]] = []
        self._exit_code = exit_code

    def __call__(
        self, _app: object, global_options: GlobalOptions, options: Options, args: Args
    ) -> int:
        self.calls.append((global_options, options, args))
        return self._exit_code


def _mode(
    handler: CommandHandler,
    *,
    argument: bool = False,
    argument_optional: bool = False,
    sub_options: Sequence[Option] = (),
) -> Mode:
    return Mode(
        long_option="test-mode",
        handler_function=handler,
        short_help="a mode under test",
        argument=argument,
        argument_descr="HOST" if argument else None,
        argument_optional=argument_optional,
        sub_options=sub_options,
    )


def _call(mode: Mode, argument: str = "", *, arguments: Sequence[str] = ()) -> int:
    return call(_APP, mode, _GLOBAL_OPTIONS, argument, [("--flag", "")], arguments, Context())


def test_a_mode_returns_its_handlers_exit_code() -> None:
    assert _call(_mode(_Recorder(exit_code=23))) == 23


def test_a_mode_without_argument_receives_no_arguments() -> None:
    handler = _Recorder()

    _call(_mode(handler), "ignored", arguments=["ignored", "too"])

    assert [args for _global_options, _options, args in handler.calls] == [()]


def test_a_required_argument_reaches_the_handler() -> None:
    handler = _Recorder()

    _call(_mode(handler, argument=True), "myhost", arguments=["myhost", "other"])

    assert [args for _global_options, _options, args in handler.calls] == [["myhost"]]


def test_the_positional_arguments_reach_the_handler() -> None:
    handler = _Recorder()

    _call(_mode(handler, argument=True, argument_optional=True), arguments=["host1", "host2"])

    assert [args for _global_options, _options, args in handler.calls] == [["host1", "host2"]]


def test_the_sub_options_reach_the_handler() -> None:
    handler = _Recorder()

    _call(_mode(handler, sub_options=_SUB_OPTIONS))

    assert [options for _global_options, options, _args in handler.calls] == [{"flag": True}]


def test_a_mode_without_sub_options_receives_none() -> None:
    handler = _Recorder()

    _call(_mode(handler))

    assert [options for _global_options, options, _args in handler.calls] == [{}]


def test_the_global_options_reach_the_handler() -> None:
    handler = _Recorder()

    _call(_mode(handler))

    assert [global_options for global_options, _options, _args in handler.calls] == [
        _GLOBAL_OPTIONS
    ]
