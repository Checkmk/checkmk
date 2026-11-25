#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
import signal
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import FrameType
from typing import Final, NoReturn, override

import pytest

from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.commands import DiscoveredCommand as CLIDiscoveredCommand
from cmk.cli.engine.discovery import _make_command as _cli_make_command
from cmk.cli.engine.output import Console as CLIConsole
from cmk.cli.engine.run import CommandTracer as CLICommandTracer
from cmk.cli.engine.run import run as cli_run
from cmk.cli.engine.run import Runtime as CLIRuntime
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

from ._commands import command_with, HANDED_IN
from ._console import FakeRunPager, FakeTerminal
from ._logger import null_logger

_CRASH_MESSAGE = "Boom: it broke - please submit a crash report! (Crash-ID: 42)"

_SITE = Path("/omd/sites/mysite")


class Recorder:
    """Stands in for a collaborator the command line only calls for its effect"""

    def __init__(self) -> None:
        self.calls: list[object] = []

    def __call__(self, *args: object) -> None:
        self.calls.append(args[0] if len(args) == 1 else args)


def _command(handler: Callable[[CLIContext, None], CLIExitCode]) -> CLIDiscoveredCommand:
    return command_with(
        CLICommand(
            name="demo",
            handler=HANDED_IN,
            long="demo",
            request=cli_no_options,
            help="Demonstrate",
        ),
        handler,
    )


class _RecordingHandler(logging.Handler):
    def __init__(self, messages: list[str]) -> None:
        super().__init__()
        self._messages = messages

    @override
    def emit(self, record: logging.LogRecord) -> None:
        self._messages.append(record.getMessage())


class FakeFileLogging:
    """Stands in for logging to the given file: records what reaches the logger instead"""

    def __init__(self) -> None:
        self.paths: list[Path] = []
        self.messages: list[str] = []

    def __call__(self, path: Path, logger: logging.Logger) -> None:
        self.paths.append(path)
        del logger.handlers[:]
        logger.addHandler(_RecordingHandler(self.messages))


def _runtime(
    commands: Sequence[CLIDiscoveredCommand] = (),
    *,
    trace_command: CLICommandTracer = lambda *_args: nullcontext(),
    on_sigint: Callable[[int, FrameType | None], object] = signal.default_int_handler,
    enable_profiling: Callable[[], None] = lambda: None,
    log_to_file: Callable[[Path, logging.Logger], None] = lambda _path, _logger: None,
    write_profile: Callable[[Path], None] = lambda _path: None,
    stdout: FakeTerminal | None = None,
    stderr: FakeTerminal | None = None,
    report_crash: Callable[[Path, Sequence[str], Mapping[str, str]], str] = (
        lambda _omd_root, _argv, _environ: _CRASH_MESSAGE
    ),
    logger: logging.Logger = null_logger(),
) -> CLIRuntime:
    return CLIRuntime(
        discover=lambda: commands,
        trace_command=trace_command,
        on_sigint=on_sigint,
        report_crash=report_crash,
        enable_profiling=enable_profiling,
        log_to_file=log_to_file,
        write_profile=write_profile,
        console=CLIConsole(
            stdout=stdout or FakeTerminal(),
            stderr=stderr or FakeTerminal(),
            environ={},
            run_pager=FakeRunPager(),
        ),
        logger=logger,
    )


def _run(argv: Sequence[str], runtime: CLIRuntime) -> int:
    previous = signal.getsignal(signal.SIGINT)
    try:
        return cli_run(_SITE, argv, {}, runtime)
    finally:
        signal.signal(signal.SIGINT, previous)


_NUMBER_VALUE: Final = CLIValue(
    long="number",
    help="A number",
    placeholder="N",
    deprecated_names=frozenset({"count"}),
    parse=int,
)


def _number_request(options: CLIReader) -> int | None:
    return options.value(_NUMBER_VALUE)


def _numbered(handler: Callable[[CLIContext, int | None], CLIExitCode]) -> CLIDiscoveredCommand:
    return command_with(
        CLICommand(
            name="demo",
            handler=HANDED_IN,
            long="demo",
            request=_number_request,
            help="Demonstrate",
        ),
        handler,
    )


def test_a_sub_option_reaches_the_command_parsed() -> None:
    seen: list[int | None] = []

    def remember(_context: CLIContext, number: int | None) -> CLIExitCode:
        seen.append(number)
        return CLIExitCode.SUCCESS

    _run(["cmk", "--demo", "--number", "5"], _runtime([_numbered(remember)]))

    assert seen == [5]


def test_a_command_reports_its_own_exit_status() -> None:
    assert _run(["cmk", "--demo"], _runtime([_command(lambda *_args: CLIExitCode.ERROR)])) == 2


def test_a_deprecated_spelling_is_reported_in_the_log_file() -> None:
    file_logging = FakeFileLogging()
    runtime = _runtime(
        [_numbered(lambda *_args: CLIExitCode.SUCCESS)],
        log_to_file=file_logging,
        logger=logging.getLogger("test_a_deprecated_spelling_is_reported_in_the_log_file"),
    )

    _run(["cmk", "--log-file=cmk.log", "--demo", "--count=5"], runtime)

    assert file_logging.messages == ["'--count' is deprecated in favour of option 'number'"]


def test_the_log_file_is_the_one_asked_for() -> None:
    file_logging = FakeFileLogging()

    _run(["cmk", "--log-file=var/log/cmk.log", "--help"], _runtime(log_to_file=file_logging))

    assert file_logging.paths == [Path("var/log/cmk.log")]


def test_a_command_is_handed_the_site_root() -> None:
    seen: list[Path] = []

    def remember(context: CLIContext, _request: None) -> CLIExitCode:
        seen.append(context.omd_root)
        return CLIExitCode.SUCCESS

    _run(["cmk", "--demo"], _runtime([_command(remember)]))

    assert seen == [_SITE]


def test_a_command_is_handed_only_the_options_it_acts_on() -> None:
    seen: list[CLIGlobalOptions] = []

    def remember(context: CLIContext, _request: None) -> CLIExitCode:
        seen.append(context.global_options)
        return CLIExitCode.SUCCESS

    _run(["cmk", "-v", "--profile", "--debug", "--demo"], _runtime([_command(remember)]))

    assert seen == [CLIGlobalOptions(debug=True)]


def test_a_command_reports_through_the_engines_logger() -> None:
    seen: list[logging.Logger] = []

    def remember(context: CLIContext, _request: None) -> CLIExitCode:
        seen.append(context.logger)
        return CLIExitCode.SUCCESS

    logger = logging.getLogger("cmk.test")
    _run(["cmk", "--demo"], _runtime([_command(remember)], logger=logger))

    assert seen == [logger.getChild("cli")]


def _unloadable() -> NoReturn:
    raise ValueError("the handler module fails to import")


def test_a_handler_that_fails_to_load_is_a_crash() -> None:
    command = _cli_make_command(
        CLICommand(
            name="demo",
            handler=HANDED_IN,
            long="demo",
            request=cli_no_options,
            help="Demonstrate",
        ),
        _unloadable,
    )

    assert _run(["cmk", "--demo"], _runtime([command])) == CLIExitCode.FAILURE.value


def test_an_unknown_option_exits_three() -> None:
    assert _run(["cmk", "--nonsense"], _runtime()) == 3


def test_an_unknown_option_says_what_it_did_not_recognise() -> None:
    stderr = FakeTerminal()

    _run(["cmk", "--nonsense"], _runtime(stderr=stderr))

    assert "--nonsense" in stderr.getvalue()


def test_the_help_exits_zero() -> None:
    assert _run(["cmk", "--help"], _runtime()) == 0


def test_the_help_is_paged() -> None:
    stdout = FakeTerminal()

    _run(["cmk", "--help"], _runtime(stdout=stdout))

    assert "WAYS TO CALL" in stdout.getvalue()


def test_the_help_names_the_commands_there_are() -> None:
    stdout = FakeTerminal()

    _run(["cmk", "--help"], _runtime([_command(lambda *_args: CLIExitCode.SUCCESS)], stdout=stdout))

    assert "--demo" in stdout.getvalue()


@pytest.fixture(name="ignored_sigint")
def _ignored_sigint() -> Iterator[None]:
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def _interrupting(_context: CLIContext, _request: None) -> CLIExitCode:
    signal.raise_signal(signal.SIGINT)
    return CLIExitCode.SUCCESS


@pytest.mark.usefixtures("ignored_sigint")
def test_an_ignored_interrupt_signal_interrupts_the_command() -> None:
    assert _run(["cmk", "--demo"], _runtime([_command(_interrupting)])) == 130


def test_the_command_line_takes_the_interrupt_signal() -> None:
    handled = Recorder()

    _run(["cmk", "--demo"], _runtime([_command(_interrupting)], on_sigint=handled))

    assert len(handled.calls) == 1


class FakeCommandTracer:
    """Stands in for the tracer that spans a command's run"""

    def __init__(self) -> None:
        self.traced: list[str] = []

    def __call__(self, _context: CLIContext, run_command: CLIRunCommand) -> nullcontext[None]:
        self.traced.append(run_command.command.name)
        return nullcontext()


def test_a_command_runs_traced() -> None:
    tracer = FakeCommandTracer()

    _run(
        ["cmk", "--demo"],
        _runtime([_command(lambda *_args: CLIExitCode.SUCCESS)], trace_command=tracer),
    )

    assert tracer.traced == ["demo"]


def test_the_command_runs_inside_its_trace() -> None:
    events: list[str] = []

    @contextmanager
    def traced(_context: CLIContext, _run_command: CLIRunCommand) -> Iterator[None]:
        events.append("trace starts")
        yield
        events.append("trace ends")

    def handler(_context: CLIContext, _request: None) -> CLIExitCode:
        events.append("handler")
        return CLIExitCode.SUCCESS

    _run(["cmk", "--demo"], _runtime([_command(handler)], trace_command=traced))

    assert events == ["trace starts", "handler", "trace ends"]


def test_the_help_is_not_traced() -> None:
    tracer = FakeCommandTracer()

    _run(["cmk", "--help"], _runtime(trace_command=tracer))

    assert not tracer.traced


def test_a_command_line_that_is_rejected_is_not_traced() -> None:
    tracer = FakeCommandTracer()

    _run(["cmk", "--nonsense"], _runtime(trace_command=tracer))

    assert not tracer.traced


def test_verbosity_raises_the_log_level() -> None:
    runtime = _runtime(logger=logging.getLogger("test_verbosity_raises_the_log_level"))

    _run(["cmk", "-v", "--help"], runtime)

    assert logging.DEBUG < runtime.logger.level < logging.INFO


def test_without_verbosity_the_logger_is_reset_to_info() -> None:
    logger = logging.getLogger("test_without_verbosity_the_logger_is_reset_to_info")
    logger.setLevel(logging.DEBUG)

    _run(["cmk", "--help"], _runtime(logger=logger))

    assert logger.level == logging.INFO


def test_profiling_is_enabled_on_request() -> None:
    enabled = Recorder()

    _run(["cmk", "--profile", "--help"], _runtime(enable_profiling=enabled))

    assert len(enabled.calls) == 1


def test_the_profile_is_written_for_the_site() -> None:
    written = Recorder()

    _run(["cmk", "--help"], _runtime(write_profile=written))

    assert written.calls == [_SITE]


def test_the_profile_is_written_even_when_the_command_raises() -> None:
    written = Recorder()

    with pytest.raises(ValueError):
        _run(
            ["cmk", "--debug", "--demo"],
            _runtime([_command(_failing)], write_profile=written),
        )

    assert len(written.calls) == 1


def _failing(_context: CLIContext, _request: None) -> CLIExitCode:
    raise ValueError("no such host")


class FakeCrashReporter:
    """Stands in for the reporter that saves a crash report and renders its message"""

    def __init__(self) -> None:
        self.reports = 0

    def __call__(self, _omd_root: Path, _argv: Sequence[str], _environ: Mapping[str, str]) -> str:
        self.reports += 1
        return _CRASH_MESSAGE


def _raising(exception: BaseException) -> Callable[[CLIContext, None], CLIExitCode]:
    def handler(_context: CLIContext, _request: None) -> CLIExitCode:
        raise exception

    return handler


def _run_demo(
    handler: Callable[[CLIContext, None], CLIExitCode],
    reporter: FakeCrashReporter | None = None,
) -> int:
    runtime = _runtime([_command(handler)], report_crash=reporter or FakeCrashReporter())
    return _run(["cmk", "--demo"], runtime)


def test_an_interrupted_command_exits_as_interrupted() -> None:
    assert _run_demo(_raising(KeyboardInterrupt())) == CLIExitCode.INTERRUPTED.value


def test_a_broken_pipe_exits_as_broken_pipe() -> None:
    broken_pipe = OSError(errno.EPIPE, "broken pipe")

    assert _run_demo(_raising(broken_pipe)) == CLIExitCode.BROKEN_PIPE.value


def test_a_broken_pipe_is_no_crash() -> None:
    reporter = FakeCrashReporter()

    _run_demo(_raising(OSError(errno.EPIPE, "broken pipe")), reporter)

    assert reporter.reports == 0


def test_any_other_os_error_exits_one() -> None:
    assert _run_demo(_raising(OSError(errno.EACCES, "denied"))) == CLIExitCode.FAILURE.value


def test_an_os_error_that_is_no_broken_pipe_is_reported() -> None:
    reporter = FakeCrashReporter()

    _run_demo(_raising(OSError(errno.EACCES, "denied")), reporter)

    assert reporter.reports == 1


def test_an_unexpected_exception_exits_one() -> None:
    assert _run_demo(_raising(ValueError("unexpected"))) == CLIExitCode.FAILURE.value


def test_an_unexpected_exception_is_reported() -> None:
    reporter = FakeCrashReporter()

    _run_demo(_raising(ValueError("unexpected")), reporter)

    assert reporter.reports == 1


def test_a_debugged_exception_is_raised_through() -> None:
    runtime = _runtime([_command(_raising(ValueError("unexpected")))])

    with pytest.raises(ValueError):
        _run(["cmk", "--debug", "--demo"], runtime)


def test_a_debugged_exception_is_not_reported() -> None:
    reporter = FakeCrashReporter()
    runtime = _runtime([_command(_raising(ValueError("unexpected")))], report_crash=reporter)

    with pytest.raises(ValueError):
        _run(["cmk", "--debug", "--demo"], runtime)

    assert reporter.reports == 0


def test_the_crash_message_reaches_the_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _run_demo(_raising(ValueError("unexpected")))

    assert _CRASH_MESSAGE in caplog.text


def test_an_interruption_says_so_in_the_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _run_demo(_raising(KeyboardInterrupt()))

    assert "<Interrupted>" in caplog.text
