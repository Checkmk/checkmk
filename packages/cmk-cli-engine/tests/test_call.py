#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Final

from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.call import call as cli_call
from cmk.cli.engine.call import CommandTracer as CLICommandTracer
from cmk.cli.engine.commands import GetoptCommand as CLIGetoptCommand
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader

from ._logger import null_logger

# The engine only hands this through to the command's handler.
_CONTEXT: Final = CLIContext(
    omd_root=Path("/omd/sites/mysite"),
    global_options=CLIGlobalOptions(verbosity=2),
    logger=null_logger(),
)

_FLAG: Final = CLIFlag(long="flag", help="a flag")


def _flag_request(options: CLIReader) -> bool:
    return options.flag(_FLAG)


class _Recorder:
    def __init__(self, exit_code: CLIExitCode = CLIExitCode.SUCCESS) -> None:
        self.calls: list[tuple[CLIContext, object, CLIArgs]] = []
        self._exit_code = exit_code

    def __call__(self, context: CLIContext, request: object, args: CLIArgs) -> CLIExitCode:
        self.calls.append((context, request, args))
        return self._exit_code


def _command(
    handler: Callable[[CLIContext, object, CLIArgs], CLIExitCode],
    *,
    arguments: CLIArguments | None = None,
    request: Callable[[CLIReader], object] = cli_no_options,
) -> CLIGetoptCommand:
    return cli_make_command(
        CLICommand(
            name="test_command",
            long="test-command",
            request=request,
            handler=handler,
            help="a command under test",
            arguments=arguments,
        )
    )


def _run_command(
    command: CLIGetoptCommand, argument: str, arguments: Sequence[str]
) -> CLIRunCommand:
    return CLIRunCommand(command, argument, [("--flag", "")], arguments)


def _call(
    command: CLIGetoptCommand,
    argument: str = "",
    *,
    arguments: Sequence[str] = (),
    traced: CLICommandTracer = lambda *_args: nullcontext(),
) -> CLIExitCode:
    run_command = _run_command(command, argument, arguments)
    return cli_call(
        _CONTEXT,
        run_command,
        command.bind(CLIParsedOptions(run_command.options, null_logger())),
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

    _call(
        _command(handler, arguments=CLIArguments("HOST")), "myhost", arguments=["myhost", "other"]
    )

    assert [args for _context, _options, args in handler.calls] == [["myhost"]]


def test_the_positional_arguments_reach_the_handler() -> None:
    handler = _Recorder()

    _call(
        _command(handler, arguments=CLIArguments("HOST", optional=True)),
        arguments=["host1", "host2"],
    )

    assert [args for _context, _options, args in handler.calls] == [["host1", "host2"]]


def test_the_request_reaches_the_handler() -> None:
    handler = _Recorder()

    _call(_command(handler, request=_flag_request))

    assert [request for _context, request, _args in handler.calls] == [True]


def test_a_command_without_options_receives_the_empty_request() -> None:
    handler = _Recorder()

    _call(_command(handler))

    assert [request for _context, request, _args in handler.calls] == [None]


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

    def handler(_context: CLIContext, _request: object, _args: CLIArgs) -> CLIExitCode:
        events.append("handler")
        return CLIExitCode.SUCCESS

    _call(_command(handler), traced=traced)

    assert events == ["trace starts", "handler", "trace ends"]


def test_the_trace_sees_what_the_handler_is_handed() -> None:
    seen: list[tuple[CLIContext, CLIRunCommand, CLIArgs]] = []

    def traced(context: CLIContext, run_command: CLIRunCommand, args: CLIArgs) -> nullcontext[None]:
        seen.append((context, run_command, args))
        return nullcontext()

    command = _command(_Recorder(), arguments=CLIArguments("HOST"), request=_flag_request)

    _call(command, "myhost", arguments=["myhost"], traced=traced)

    assert seen == [(_CONTEXT, _run_command(command, "myhost", ["myhost"]), ["myhost"])]
