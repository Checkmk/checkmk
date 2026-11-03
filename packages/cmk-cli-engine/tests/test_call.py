#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Final

from cmk.cli.engine.call import call, CommandTracer
from cmk.cli.engine.commands import Command, Option, parse_sub_options
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import CommandHandler, Options
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions

from ._logger import null_logger

# The engine only hands this through to the command's handler.
_CONTEXT: Final = CLIContext(
    omd_root=Path("/omd/sites/mysite"),
    global_options=CLIGlobalOptions(verbosity=2),
    logger=null_logger(),
)

_SUB_OPTIONS: Final = [Option(long_option="flag", short_help="a flag")]


class _Recorder:
    def __init__(self, exit_code: CLIExitCode = CLIExitCode.SUCCESS) -> None:
        self.calls: list[tuple[CLIContext, Options, CLIArgs]] = []
        self._exit_code = exit_code

    def __call__(self, context: CLIContext, options: Options, args: CLIArgs) -> CLIExitCode:
        self.calls.append((context, options, args))
        return self._exit_code


def _command(
    handler: CommandHandler,
    *,
    argument: bool = False,
    argument_optional: bool = False,
    sub_options: Sequence[Option] = (),
) -> Command:
    return Command(
        name="test_command",
        long_option="test-command",
        handler_function=handler,
        short_help="a command under test",
        argument=argument,
        argument_descr="HOST" if argument else None,
        argument_optional=argument_optional,
        sub_options=sub_options,
    )


def _call(
    command: Command,
    argument: str = "",
    *,
    arguments: Sequence[str] = (),
    traced: CommandTracer = lambda *_args: nullcontext(),
) -> CLIExitCode:
    return call(
        _CONTEXT,
        command,
        argument,
        parse_sub_options(command.sub_options, [("--flag", "")], null_logger()),
        arguments,
        traced,
    )


def test_a_command_returns_its_handlers_exit_code() -> None:
    assert _call(_command(_Recorder(exit_code=CLIExitCode.ERROR))) == CLIExitCode.ERROR


def test_a_command_without_argument_receives_no_arguments() -> None:
    handler = _Recorder()

    _call(_command(handler), "ignored", arguments=["ignored", "too"])

    assert [args for _context, _options, args in handler.calls] == [()]


def test_a_required_argument_reaches_the_handler() -> None:
    handler = _Recorder()

    _call(_command(handler, argument=True), "myhost", arguments=["myhost", "other"])

    assert [args for _context, _options, args in handler.calls] == [["myhost"]]


def test_the_positional_arguments_reach_the_handler() -> None:
    handler = _Recorder()

    _call(_command(handler, argument=True, argument_optional=True), arguments=["host1", "host2"])

    assert [args for _context, _options, args in handler.calls] == [["host1", "host2"]]


def test_the_sub_options_reach_the_handler() -> None:
    handler = _Recorder()

    _call(_command(handler, sub_options=_SUB_OPTIONS))

    assert [options for _context, options, _args in handler.calls] == [{"flag": True}]


def test_a_command_without_sub_options_receives_none() -> None:
    handler = _Recorder()

    _call(_command(handler))

    assert [options for _context, options, _args in handler.calls] == [{}]


def test_the_context_reaches_the_handler() -> None:
    handler = _Recorder()

    _call(_command(handler))

    assert [context for context, _options, _args in handler.calls] == [_CONTEXT]


def test_the_handler_runs_inside_the_commands_trace() -> None:
    events: list[str] = []

    @contextmanager
    def traced(*_args: object) -> Iterator[None]:
        events.append("trace starts")
        yield
        events.append("trace ends")

    def handler(_context: CLIContext, _options: Options, _args: CLIArgs) -> CLIExitCode:
        events.append("handler")
        return CLIExitCode.SUCCESS

    _call(_command(handler), traced=traced)

    assert events == ["trace starts", "handler", "trace ends"]


def test_the_trace_sees_what_the_handler_is_handed() -> None:
    seen: list[tuple[CLIContext, Command, Options, CLIArgs]] = []

    def traced(
        context: CLIContext, command: Command, options: Options, args: CLIArgs
    ) -> nullcontext[None]:
        seen.append((context, command, options, args))
        return nullcontext()

    command = _command(_Recorder(), argument=True, sub_options=_SUB_OPTIONS)

    _call(command, "myhost", arguments=["myhost"], traced=traced)

    assert seen == [(_CONTEXT, command, {"flag": True}, ["myhost"])]
