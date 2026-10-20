#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import signal
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from types import FrameType

import pytest

from cmk.cli.engine.commands import Command, make_command
from cmk.cli.engine.run import (
    dispatch,
    enable_file_logging,
    log_level,
    run,
    Runtime,
)
from cmk.cli.internal import (
    Args,
    CLICommand,
    CLIOption,
    CommandContext,
    CommandHandler,
    ExitCode,
    Options,
)

from ._logger import null_logger

_CRASH_MESSAGE = "Boom: it broke - please submit a crash report! (Crash-ID: 42)"

_SITE = Path("/omd/sites/mysite")


class FakeCrashReporter:
    """Stands in for the reporter that saves a crash report and renders its message"""

    def __init__(self) -> None:
        self.reports = 0

    def __call__(self) -> str:
        self.reports += 1
        return _CRASH_MESSAGE


class Recorder:
    """Stands in for a collaborator the command line only calls for its effect"""

    def __init__(self) -> None:
        self.calls: list[object] = []

    def __call__(self, *args: object) -> None:
        self.calls.append(args[0] if len(args) == 1 else args)


def _raising(exception: BaseException) -> Callable[[], ExitCode]:
    def command() -> ExitCode:
        raise exception

    return command


def _dispatch(
    command: Callable[[], ExitCode], reporter: FakeCrashReporter | None = None
) -> ExitCode:
    return dispatch(command, null_logger(), reporter or FakeCrashReporter(), debug=False)


def test_the_exit_status_of_a_command_that_succeeds_is_its_own() -> None:
    assert _dispatch(lambda: ExitCode.ERROR) == ExitCode.ERROR


def test_an_interrupted_command_exits_as_interrupted() -> None:
    assert _dispatch(_raising(KeyboardInterrupt())) == ExitCode.INTERRUPTED


def test_a_broken_pipe_exits_as_broken_pipe() -> None:
    assert _dispatch(_raising(OSError(errno.EPIPE, "broken pipe"))) == ExitCode.BROKEN_PIPE


def test_a_broken_pipe_is_no_crash() -> None:
    reporter = FakeCrashReporter()

    _dispatch(_raising(OSError(errno.EPIPE, "broken pipe")), reporter)

    assert reporter.reports == 0


def test_any_other_os_error_exits_one() -> None:
    assert _dispatch(_raising(OSError(errno.EACCES, "denied"))) == ExitCode.FAILURE


def test_an_os_error_that_is_no_broken_pipe_is_reported() -> None:
    reporter = FakeCrashReporter()

    _dispatch(_raising(OSError(errno.EACCES, "denied")), reporter)

    assert reporter.reports == 1


def test_an_unexpected_exception_exits_one() -> None:
    assert _dispatch(_raising(ValueError("unexpected"))) == ExitCode.FAILURE


def test_an_unexpected_exception_is_reported() -> None:
    reporter = FakeCrashReporter()

    _dispatch(_raising(ValueError("unexpected")), reporter)

    assert reporter.reports == 1


def test_a_debugged_exception_is_raised_through() -> None:
    with pytest.raises(ValueError):
        dispatch(_raising(ValueError("unexpected")), null_logger(), FakeCrashReporter(), debug=True)


def test_a_debugged_exception_is_not_reported() -> None:
    reporter = FakeCrashReporter()

    with pytest.raises(ValueError):
        dispatch(_raising(ValueError("unexpected")), null_logger(), reporter, debug=True)

    assert reporter.reports == 0


def test_the_crash_message_reaches_the_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _dispatch(_raising(ValueError("unexpected")))

    assert _CRASH_MESSAGE in caplog.text


def test_an_interruption_says_so_in_the_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _dispatch(_raising(KeyboardInterrupt()))

    assert "<Interrupted>" in caplog.text


def test_without_verbosity_the_log_level_is_info() -> None:
    assert log_level(0) == logging.INFO


def test_one_verbosity_is_more_than_info() -> None:
    assert logging.DEBUG < log_level(1) < logging.INFO


def test_two_verbosities_are_debug() -> None:
    assert log_level(2) == logging.DEBUG


def test_more_verbosity_than_we_know_stays_debug() -> None:
    assert log_level(23) == logging.DEBUG


def test_file_logging_writes_to_the_given_file(tmp_path: Path) -> None:
    logger = logging.getLogger("test_file_logging_writes_to_the_given_file")
    path = tmp_path / "logs" / "cmk.log"

    enable_file_logging(str(path), logger)
    logger.error("a message")

    assert "a message" in path.read_text()


def test_file_logging_replaces_the_handlers_it_finds(tmp_path: Path) -> None:
    logger = logging.getLogger("test_file_logging_replaces_the_handlers_it_finds")
    logger.addHandler(logging.NullHandler())

    enable_file_logging(str(tmp_path / "cmk.log"), logger)

    assert len(logger.handlers) == 1


def _command(handler: CommandHandler) -> Command:
    return make_command(
        CLICommand(long_option="demo", handler_function=handler, short_help="Demonstrate")
    )


def _runtime(
    commands: Sequence[Command] = (),
    *,
    start_tracing: Callable[[Path], None] = lambda _omd_root: None,
    on_sigint: Callable[[int, FrameType | None], object] = signal.default_int_handler,
    enable_profiling: Callable[[], None] = lambda: None,
    write_profile: Callable[[Path], None] = lambda _path: None,
    page: Callable[[str], None] = lambda _text: None,
    write: Callable[[str], None] = lambda _text: None,
    logger: logging.Logger = null_logger(),
) -> Runtime:
    return Runtime(
        discover=lambda: commands,
        start_tracing=start_tracing,
        on_sigint=on_sigint,
        crash_reporter_for=lambda _omd_root, _argv, _environ: FakeCrashReporter(),
        enable_profiling=enable_profiling,
        write_profile=write_profile,
        page=page,
        write=write,
        logger=logger,
    )


def _run(argv: Sequence[str], runtime: Runtime) -> int:
    previous = signal.getsignal(signal.SIGINT)
    try:
        return run(_SITE, argv, {}, runtime)
    finally:
        signal.signal(signal.SIGINT, previous)


def _numbered(handler: CommandHandler) -> Command:
    return make_command(
        CLICommand(
            long_option="demo",
            handler_function=handler,
            short_help="Demonstrate",
            sub_options=[
                CLIOption(
                    long_option="number",
                    short_help="A number",
                    argument=True,
                    argument_descr="N",
                    argument_conv=int,
                )
            ],
        )
    )


def test_a_sub_option_reaches_the_command_converted() -> None:
    seen: list[Options] = []

    def remember(_context: CommandContext, sub: Options, _args: Args) -> ExitCode:
        seen.append(sub)
        return ExitCode.SUCCESS

    _run(["cmk", "--demo", "--number", "5"], _runtime([_numbered(remember)]))

    assert seen == [{"number": 5}]


def test_a_command_reports_its_own_exit_status() -> None:
    assert _run(["cmk", "--demo"], _runtime([_command(lambda *_args: ExitCode.ERROR)])) == 2


def test_a_sub_option_argument_the_conversion_rejects_exits_three() -> None:
    command = _numbered(lambda *_args: ExitCode.SUCCESS)

    assert _run(["cmk", "--demo", "--number", "x"], _runtime([command])) == 3


def test_a_sub_option_argument_the_conversion_rejects_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runtime = _runtime(
        [_numbered(lambda *_args: ExitCode.SUCCESS)], logger=logging.getLogger("cmk.test")
    )

    with caplog.at_level(logging.ERROR):
        _run(["cmk", "--demo", "--number", "x"], runtime)

    assert caplog.messages == ["--number: Invalid argument"]


def test_a_sub_option_argument_the_conversion_rejects_is_raised_through_under_debug() -> None:
    runtime = _runtime([_numbered(lambda *_args: ExitCode.SUCCESS)])

    with pytest.raises(ValueError, match="--number: Invalid argument"):
        _run(["cmk", "--debug", "--demo", "--number", "x"], runtime)


def test_a_command_is_handed_the_site_root() -> None:
    seen: list[Path] = []

    def remember(context: CommandContext, _sub: Options, _args: Args) -> ExitCode:
        seen.append(context.omd_root)
        return ExitCode.SUCCESS

    _run(["cmk", "--demo"], _runtime([_command(remember)]))

    assert seen == [_SITE]


def test_a_command_reports_through_the_engines_logger() -> None:
    seen: list[logging.Logger] = []

    def remember(context: CommandContext, _sub: Options, _args: Args) -> ExitCode:
        seen.append(context.logger)
        return ExitCode.SUCCESS

    logger = logging.getLogger("cmk.test")
    _run(["cmk", "--demo"], _runtime([_command(remember)], logger=logger))

    assert seen == [logger.getChild("base")]


def test_an_unknown_option_exits_three() -> None:
    assert _run(["cmk", "--nonsense"], _runtime()) == 3


def test_an_unknown_option_says_what_it_did_not_recognise() -> None:
    written = Recorder()

    _run(["cmk", "--nonsense"], _runtime(write=written))

    assert "--nonsense" in str(written.calls[0])


def test_the_help_exits_zero() -> None:
    assert _run(["cmk", "--help"], _runtime()) == 0


def test_the_help_is_paged() -> None:
    paged = Recorder()

    _run(["cmk", "--help"], _runtime(page=paged))

    assert "WAYS TO CALL" in str(paged.calls[0])


def test_the_help_names_the_commands_there_are() -> None:
    paged = Recorder()

    _run(["cmk", "--help"], _runtime([_command(lambda *_args: ExitCode.SUCCESS)], page=paged))

    assert "--demo" in str(paged.calls[0])


@pytest.fixture(name="ignored_sigint")
def _ignored_sigint() -> Iterator[None]:
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def _interrupting(_context: CommandContext, _sub: Options, _args: Args) -> ExitCode:
    signal.raise_signal(signal.SIGINT)
    return ExitCode.SUCCESS


@pytest.mark.usefixtures("ignored_sigint")
def test_an_ignored_interrupt_signal_interrupts_the_command() -> None:
    assert _run(["cmk", "--demo"], _runtime([_command(_interrupting)])) == 130


def test_the_command_line_takes_the_interrupt_signal() -> None:
    handled = Recorder()

    _run(["cmk", "--demo"], _runtime([_command(_interrupting)], on_sigint=handled))

    assert len(handled.calls) == 1


def test_tracing_starts_for_the_site_when_a_command_runs() -> None:
    started = Recorder()

    _run(
        ["cmk", "--demo"],
        _runtime([_command(lambda *_args: ExitCode.SUCCESS)], start_tracing=started),
    )

    assert started.calls == [_SITE]


def test_the_help_is_not_traced() -> None:
    started = Recorder()

    _run(["cmk", "--help"], _runtime(start_tracing=started))

    assert not started.calls


def test_a_command_line_that_is_rejected_is_not_traced() -> None:
    started = Recorder()

    _run(["cmk", "--nonsense"], _runtime(start_tracing=started))

    assert not started.calls


def test_verbosity_raises_the_log_level() -> None:
    runtime = _runtime()

    _run(["cmk", "-v", "--help"], runtime)

    assert runtime.logger.level == log_level(1)


def test_profiling_is_enabled_on_request() -> None:
    enabled = Recorder()

    _run(["cmk", "--profile", "--help"], _runtime(enable_profiling=enabled))

    assert len(enabled.calls) == 1


def test_the_profile_is_written_below_the_site() -> None:
    written = Recorder()

    _run(["cmk", "--help"], _runtime(write_profile=written))

    assert written.calls == [_SITE / "var/check_mk/web"]


def test_the_profile_is_written_even_when_the_command_raises() -> None:
    written = Recorder()

    with pytest.raises(ValueError):
        _run(
            ["cmk", "--debug", "--demo"],
            _runtime([_command(_failing)], write_profile=written),
        )

    assert len(written.calls) == 1


def _failing(_context: CommandContext, _sub_options: Options, _args: Args) -> ExitCode:
    raise ValueError("no such host")
