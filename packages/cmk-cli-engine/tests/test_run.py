#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKBailOut, MKGeneralException, MKTerminate
from cmk.cli.engine.commands import make_mode, Mode
from cmk.cli.engine.run import dispatch, enable_file_logging, log_level, run, Runtime
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options

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


def _raising(exception: Exception) -> Callable[[], int]:
    def command() -> int:
        raise exception

    return command


def _dispatch(command: Callable[[], int], reporter: FakeCrashReporter | None = None) -> int:
    return dispatch(command, null_logger(), reporter or FakeCrashReporter(), lambda: False)


def test_the_exit_status_of_a_command_that_succeeds_is_its_own() -> None:
    assert _dispatch(lambda: 2) == 2


def test_an_interrupted_command_exits_one() -> None:
    assert _dispatch(_raising(MKTerminate())) == 1


def test_a_general_exception_exits_three() -> None:
    assert _dispatch(_raising(MKGeneralException("no such host"))) == 3


def test_a_bail_out_exits_three() -> None:
    assert _dispatch(_raising(MKBailOut("no such host"))) == 3


def test_a_broken_pipe_exits_four() -> None:
    assert _dispatch(_raising(OSError(errno.EPIPE, "broken pipe"))) == 4


def test_a_broken_pipe_is_no_crash() -> None:
    reporter = FakeCrashReporter()

    _dispatch(_raising(OSError(errno.EPIPE, "broken pipe")), reporter)

    assert reporter.reports == 0


def test_any_other_os_error_exits_one() -> None:
    assert _dispatch(_raising(OSError(errno.EACCES, "denied"))) == 1


def test_an_os_error_that_is_no_broken_pipe_is_reported() -> None:
    reporter = FakeCrashReporter()

    _dispatch(_raising(OSError(errno.EACCES, "denied")), reporter)

    assert reporter.reports == 1


def test_an_unexpected_exception_exits_one() -> None:
    assert _dispatch(_raising(ValueError("unexpected"))) == 1


def test_an_unexpected_exception_is_reported() -> None:
    reporter = FakeCrashReporter()

    _dispatch(_raising(ValueError("unexpected")), reporter)

    assert reporter.reports == 1


def test_a_debugged_exception_is_raised_through() -> None:
    with pytest.raises(ValueError):
        dispatch(
            _raising(ValueError("unexpected")), null_logger(), FakeCrashReporter(), lambda: True
        )


def test_the_crash_message_reaches_the_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _dispatch(_raising(ValueError("unexpected")))

    assert _CRASH_MESSAGE in caplog.text


def test_an_interruption_says_so_in_the_log(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _dispatch(_raising(MKTerminate()))

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


def _command(handler: Callable[[Path, GlobalOptions, Options, Args], int]) -> Mode:
    return make_mode(
        CLICommand(long_option="demo", handler_function=handler, short_help="Demonstrate")
    )


def _runtime(
    commands: Sequence[Mode] = (),
    *,
    start_tracing: Callable[[Path], None] = lambda _omd_root: None,
    on_sigint: Callable[[], None] = lambda: None,
    enable_debug: Callable[[], None] = lambda: None,
    debug_enabled: Callable[[], bool] = lambda: False,
    enable_profiling: Callable[[], None] = lambda: None,
    write_profile: Callable[[Path], None] = lambda _path: None,
    page: Callable[[str], None] = lambda _text: None,
    write: Callable[[str], None] = lambda _text: None,
) -> Runtime:
    return Runtime(
        discover=lambda: commands,
        start_tracing=start_tracing,
        on_sigint=on_sigint,
        crash_reporter_for=lambda _omd_root, _argv, _environ: FakeCrashReporter(),
        enable_debug=enable_debug,
        debug_enabled=debug_enabled,
        enable_profiling=enable_profiling,
        write_profile=write_profile,
        page=page,
        write=write,
        logger=null_logger(),
    )


def _run(argv: Sequence[str], runtime: Runtime) -> int:
    return run(_SITE, argv, {}, runtime)


def test_a_command_reports_its_own_exit_status() -> None:
    assert _run(["cmk", "--demo"], _runtime([_command(lambda *_args: 2)])) == 2


def test_a_command_is_handed_the_site_root() -> None:
    seen: list[Path] = []

    def remember(omd_root: Path, _options: GlobalOptions, _sub: Options, _args: Args) -> int:
        seen.append(omd_root)
        return 0

    _run(["cmk", "--demo"], _runtime([_command(remember)]))

    assert seen == [_SITE]


def test_an_unknown_option_exits_one() -> None:
    assert _run(["cmk", "--nonsense"], _runtime()) == 1


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

    _run(["cmk", "--help"], _runtime([_command(lambda *_args: 0)], page=paged))

    assert "--demo" in str(paged.calls[0])


def test_the_command_line_takes_the_interrupt_signal() -> None:
    installed = Recorder()

    _run(["cmk", "--help"], _runtime(on_sigint=installed))

    assert len(installed.calls) == 1


def test_tracing_starts_for_the_site() -> None:
    started = Recorder()

    _run(["cmk", "--help"], _runtime(start_tracing=started))

    assert started.calls == [_SITE]


def test_verbosity_raises_the_log_level() -> None:
    runtime = _runtime()

    _run(["cmk", "-v", "--help"], runtime)

    assert runtime.logger.level == log_level(1)


def test_debug_is_enabled_on_request() -> None:
    enabled = Recorder()

    _run(["cmk", "--debug", "--help"], _runtime(enable_debug=enabled))

    assert len(enabled.calls) == 1


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

    with pytest.raises(MKGeneralException):
        _run(
            ["cmk", "--demo"],
            _runtime([_command(_failing)], debug_enabled=lambda: True, write_profile=written),
        )

    assert len(written.calls) == 1


def _failing(_omd_root: Path, _options: GlobalOptions, _sub_options: Options, _args: Args) -> int:
    raise MKGeneralException("no such host")
