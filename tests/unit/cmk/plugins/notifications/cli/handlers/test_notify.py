#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.automations.backends.helper import AutomationHelperUnavailable
from cmk.ccc.exceptions import MKGeneralException, MKTerminate
from cmk.ccc.version import Edition
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.plugins.notifications.cli.handlers.notify import (
    _NotifyCommand,
)
from cmk.plugins.notifications.cli.notify import NotifyRequest


class _FakeEditionOf:
    def __init__(self, edition: Edition) -> None:
        self.asked: list[Path] = []
        self._edition = edition

    def __call__(self, omd_root: Path) -> Edition:
        self.asked.append(omd_root)
        return self._edition


class _FakeExecuteNotifyAutomation:
    def __init__(self, output: str = "{'exit_code': 0, 'output': ''}") -> None:
        self.asked: list[Sequence[str]] = []
        self._output = output

    def __call__(self, args: Sequence[str]) -> str:
        self.asked.append(args)
        return self._output


class _UnavailableNotifyAutomation:
    def __call__(self, args: Sequence[str]) -> str:
        raise AutomationHelperUnavailable(f"No automation helper for {args}")


class _FakeNotify:
    def __init__(self, result: int | None = 0, error: Exception | None = None) -> None:
        self.asked: list[tuple[Sequence[str], Path, Edition, bool, bool, bool]] = []
        self._result = result
        self._error = error

    def __call__(
        self,
        args: Sequence[str],
        *,
        omd_root: Path,
        edition: Edition,
        log_to_stdout: bool,
        keepalive: bool,
        debug: bool,
    ) -> int | None:
        self.asked.append((args, omd_root, edition, log_to_stdout, keepalive, debug))
        if self._error is not None:
            raise self._error
        return self._result


def _notify_command(
    *,
    edition: Edition = Edition.PRO,
    automation_helper_enabled: bool = True,
    execute_automation: _FakeExecuteNotifyAutomation | _UnavailableNotifyAutomation | None = None,
    notify: _FakeNotify | None = None,
) -> _NotifyCommand:
    return _NotifyCommand(
        edition_of=_FakeEditionOf(edition),
        automation_helper_enabled=lambda _omd_root: automation_helper_enabled,
        execute_automation=execute_automation or _FakeExecuteNotifyAutomation(),
        notify=notify or _FakeNotify(),
    )


_OMD_ROOT = Path("/omd/sites/mysite")


def _context(*, debug: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=_OMD_ROOT,
        global_options=CLIGlobalOptions(debug=debug),
        logger=logging.getLogger(__name__),
    )


def _request(*arguments: str, log_to_stdout: bool = False) -> NotifyRequest:
    return NotifyRequest(log_to_stdout=log_to_stdout, keepalive=False, arguments=arguments)


@pytest.mark.parametrize(
    ["returncode", "expected"],
    [
        pytest.param(None, CLIExitCode.SUCCESS, id="no result"),
        pytest.param(0, CLIExitCode.SUCCESS, id="success"),
        pytest.param(1, CLIExitCode.FAILURE, id="temporary failure"),
        pytest.param(2, CLIExitCode.ERROR, id="permanent failure"),
        pytest.param(127, CLIExitCode.ERROR, id="missing interpreter"),
        pytest.param(-9, CLIExitCode.ERROR, id="killed script"),
    ],
)
def test_a_notification_script_result_keeps_its_retry_meaning(
    returncode: int | None, expected: CLIExitCode
) -> None:
    notify = _FakeNotify(result=returncode)

    assert _notify_command(notify=notify).run(_context(), _request("fake-service")) == expected


_SPOOLFILE = ("spoolfile", "/spool/1")


def test_a_notification_is_sent_with_the_command_line_arguments() -> None:
    notify = _FakeNotify()

    _notify_command(notify=notify).run(_context(), _request("fake-service"))

    assert notify.asked == [(("fake-service",), _OMD_ROOT, Edition.PRO, False, False, False)]


def test_a_spool_file_of_a_commercial_site_goes_to_the_automation_helper() -> None:
    execute = _FakeExecuteNotifyAutomation()

    _notify_command(execute_automation=execute).run(_context(), _request(*_SPOOLFILE))

    assert execute.asked == [_SPOOLFILE]


def test_the_automation_helper_is_asked_to_log_to_stdout_as_well() -> None:
    execute = _FakeExecuteNotifyAutomation()
    request = _request(*_SPOOLFILE, log_to_stdout=True)

    _notify_command(execute_automation=execute).run(_context(), request)

    assert execute.asked == [["--log-to-stdout", *_SPOOLFILE]]


def test_a_spool_file_of_a_community_site_is_notified_locally() -> None:
    notify = _FakeNotify()
    notification = _notify_command(edition=Edition.COMMUNITY, notify=notify)

    notification.run(_context(), _request(*_SPOOLFILE))

    assert notify.asked == [(_SPOOLFILE, _OMD_ROOT, Edition.COMMUNITY, False, False, False)]


def test_a_spool_file_is_notified_locally_when_the_automation_helper_is_disabled() -> None:
    execute = _FakeExecuteNotifyAutomation()
    notify = _FakeNotify()
    notification = _notify_command(
        automation_helper_enabled=False, execute_automation=execute, notify=notify
    )

    notification.run(_context(), _request(*_SPOOLFILE))

    assert (execute.asked, notify.asked) == (
        [],
        [(_SPOOLFILE, _OMD_ROOT, Edition.PRO, False, False, False)],
    )


def test_a_spool_file_fails_when_the_enabled_automation_helper_is_unreachable() -> None:
    notification = _notify_command(execute_automation=_UnavailableNotifyAutomation())

    assert notification.run(_context(), _request(*_SPOOLFILE)) == CLIExitCode.FAILURE


def test_the_automation_helpers_exit_code_keeps_its_retry_meaning() -> None:
    execute = _FakeExecuteNotifyAutomation("{'exit_code': 1, 'output': ''}")

    assert (
        _notify_command(execute_automation=execute).run(_context(), _request(*_SPOOLFILE))
        == CLIExitCode.FAILURE
    )


def test_the_automation_helpers_output_is_written_when_logging_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    execute = _FakeExecuteNotifyAutomation("{'exit_code': 0, 'output': 'sent\\n'}")
    request = _request(*_SPOOLFILE, log_to_stdout=True)

    _notify_command(execute_automation=execute).run(_context(), request)

    assert capsys.readouterr().out == "sent\n"


def test_an_unparsable_automation_result_exits_two() -> None:
    execute = _FakeExecuteNotifyAutomation("not python")

    assert (
        _notify_command(execute_automation=execute).run(_context(), _request(*_SPOOLFILE))
        == CLIExitCode.ERROR
    )


def test_a_failing_notification_exits_three() -> None:
    notify = _FakeNotify(error=MKGeneralException("Cannot load the configuration"))

    assert _notify_command(notify=notify).run(_context(), _request()) == CLIExitCode.UNKNOWN


def test_a_failing_notification_is_raised_through_under_debug() -> None:
    notify = _FakeNotify(error=MKGeneralException("Cannot load the configuration"))

    with pytest.raises(MKGeneralException, match="Cannot load the configuration"):
        _notify_command(notify=notify).run(_context(debug=True), _request())


def test_an_interrupted_notification_exits_as_interrupted() -> None:
    notify = _FakeNotify(error=MKTerminate())

    assert _notify_command(notify=notify).run(_context(), _request()) == CLIExitCode.INTERRUPTED
