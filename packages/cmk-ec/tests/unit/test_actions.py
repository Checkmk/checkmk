#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Running the commands of the actions of the EC"""

import array
import fcntl
import logging
import math
import os
import shlex
import signal
import subprocess
import termios
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import suppress
from pathlib import Path
from typing import override

import pytest

import cmk.ec.export as ec
from cmk.ec.actions import ActionRunner, do_event_action, do_notify, run_in_subprocess
from cmk.ec.config import (
    Action,
    Config,
    EMailAction,
    EMailActionConfig,
    ScriptAction,
    ScriptActionConfig,
)
from cmk.ec.event import Event
from cmk.ec.history import HistoryWhat
from cmk.ec.host_config import HostConfig
from cmk.ec.main import StatusTableEvents

from .helpers import FakeConnection, new_event, put_on_path, RecordingHistory, wait_until_exists

_LOGGER = logging.getLogger("cmk.mkeventd")

# For commands which hang right away, so it doesn't matter how fast they start
_SHORT_TIMEOUT = 0.1  # seconds

# For a clock standing still until the script is ready, see _run_script_timing_out_once()
_TIMEOUT_ONCE_READY = 0.01  # seconds


def _run_script(script: str, *, timeout: float = 30) -> None:
    run_in_subprocess(
        args=["/bin/sh"],
        input_=script,
        env=None,
        description="executing script",
        logger=_LOGGER,
        timeout=timeout,
    )


def _run_script_timing_out_once_ready(script: str, ready: Path) -> bool:
    """Runs the script, timing out once it has created the file, however long that takes"""
    return _run_script_timing_out_once(script, lambda _process: ready.exists())


def _run_script_timing_out_once_exited(script: str) -> bool:
    """Runs the script, timing out once it has exited, however long that takes"""
    return _run_script_timing_out_once(script, lambda process: not _is_running(process.pid))


def _run_script_timing_out_once_released(script: str, running: Path, released: Path) -> bool:
    """Runs the script, which creates the 1st file and waits for the 2nd one, timing out once it
    has exited after getting released"""

    def exited_once_released(process: subprocess.Popen[str]) -> bool:
        if not running.exists():
            return False
        released.touch()
        return _ends_soon(process.pid)

    return _run_script_timing_out_once(script, exited_once_released)


def _run_script_timing_out_once(
    script: str, ready: Callable[[subprocess.Popen[str]], bool]
) -> bool:
    """
    Runs the script, timing out once it's ready and its output so far has been read, however long
    that takes, but failing after 30 s of real time
    """
    started: list[subprocess.Popen[str]] = []
    real_deadline = time.monotonic() + 30
    jumped = False

    def done(process: subprocess.Popen[str]) -> bool:
        assert process.stdout is not None
        # Its output from before getting ready is in the pipe then, unless it has been read.
        return ready(process) and _bytes_in_pipe(process.stdout.fileno()) == 0

    def clock() -> float:
        nonlocal jumped
        if started and done(started[0]):
            return math.inf
        if time.monotonic() >= real_deadline:
            jumped = True
            return math.inf
        return 0.0

    finished = run_in_subprocess(
        args=["/bin/sh"],
        input_=script,
        env=None,
        description="executing script",
        logger=_LOGGER,
        timeout=_TIMEOUT_ONCE_READY,
        clock=clock,
        on_start=started.append,
    )
    assert not jumped, "the script didn't get ready within 30 s"
    return finished


def _bytes_in_pipe(fd: int) -> int:
    count = array.array("i", [0])
    fcntl.ioctl(fd, termios.FIONREAD, count)
    return count[0]


def _run_script_later(action_runner: ActionRunner, script: str) -> None:
    action_runner.run(
        args=["/bin/sh"], input_=script, env=None, description="executing script", logger=_LOGGER
    )


def test_successful_command_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    _run_script("true")

    assert caplog.messages == ["executing script succeeded"]


def test_failed_command_is_logged_with_its_exit_code_and_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    _run_script("echo disk full; echo no space left >&2; exit 3")

    assert caplog.messages == [
        "executing script failed with exit code 3",
        "  output: disk full",
        "  output: no space left",
    ]


def test_command_not_finishing_in_time_is_killed_and_logged_with_its_output(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    ready = tmp_path / "ready"

    _run_script_timing_out_once_ready(
        f"echo started; touch {shlex.quote(str(ready))}; exec sleep 60", ready
    )

    assert caplog.messages == [
        "executing script didn't finish within 0.01 s, killed it",
        "  output: started",
    ]


def test_killed_command_is_logged_with_its_output_although_that_isnt_utf_8(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    ready = tmp_path / "ready"

    # "caf\351" is "café" in Latin-1.
    _run_script_timing_out_once_ready(
        f"printf 'caf\\351\\n'; touch {shlex.quote(str(ready))}; exec sleep 60", ready
    )

    assert caplog.messages == [
        "executing script didn't finish within 0.01 s, killed it",
        "  output: caf\ufffd",
    ]


def test_command_not_finishing_in_time_is_killed_with_the_processes_it_started(
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "pid"
    ready = tmp_path / "ready"

    # Without the output of the script, which would keep waiting for the started process anyway
    script = (
        f"sleep 60 >/dev/null 2>&1 & echo $! > {shlex.quote(str(pid_file))}; "
        f"touch {shlex.quote(str(ready))}; wait"
    )

    try:
        _run_script_timing_out_once_ready(script, ready)
        ends_soon = _ends_soon(int(pid_file.read_text()))
    finally:
        with suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)

    assert ends_soon


def test_killed_command_doesnt_wait_for_a_process_it_started_in_a_session_of_its_own(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pid_file = tmp_path / "pid"
    ready = tmp_path / "ready"
    # The started process keeps the output of the script open, but killing the script misses it.
    script = (
        f"echo started; setsid sleep 60 & echo $! > {shlex.quote(str(pid_file))}; "
        f"touch {shlex.quote(str(ready))}; wait"
    )

    try:
        _run_script_timing_out_once_ready(script, ready)
        still_running = _is_running(int(pid_file.read_text()))
    finally:
        with suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)

    assert (still_running, caplog.messages) == (
        True,
        ["executing script didn't finish within 0.01 s, killed it", "  output: started"],
    )


def test_command_leaving_processes_which_keep_its_output_open_counts_as_finished(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    pid_file = tmp_path / "pid"
    # The started process keeps the output of the script open after the script has exited.
    script = f"echo started; sleep 60 & echo $! > {shlex.quote(str(pid_file))}"

    try:
        finished = _run_script_timing_out_once_exited(script)
    finally:
        with suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)

    assert (finished, caplog.messages) == (
        True,
        [
            (
                "executing script left processes keeping its output open after 0.01 s, killed "
                "those in its process group"
            ),
            "  output: started",
        ],
    )


def test_processes_keeping_the_output_of_a_finished_command_open_are_killed(
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "pid"

    try:
        _run_script_timing_out_once_exited(f"sleep 60 & echo $! > {shlex.quote(str(pid_file))}")
        ends_soon = _ends_soon(int(pid_file.read_text()))
    finally:
        with suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)

    assert ends_soon


def test_command_finishing_right_at_its_deadline_succeeds(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    running = tmp_path / "running"
    released = tmp_path / "released"
    script = (
        f"touch {shlex.quote(str(running))}; "
        f"until [ -e {shlex.quote(str(released))} ]; do sleep 0.01; done"
    )

    finished = _run_script_timing_out_once_released(script, running, released)

    assert (finished, caplog.messages) == (True, ["executing script succeeded"])


def test_command_gets_killed_if_running_it_fails() -> None:
    started: list[subprocess.Popen[str]] = []

    def fail_on_start(process: subprocess.Popen[str]) -> None:
        started.append(process)
        raise MemoryError  # like collecting the output of a command printing nonstop

    with pytest.raises(MemoryError):
        run_in_subprocess(
            args=["sleep", "60"],
            input_="",
            env=None,
            description="executing script",
            logger=_LOGGER,
            timeout=30,
            on_start=fail_on_start,
        )

    assert started[0].returncode == -signal.SIGKILL


def _run_command_hard_to_kill(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> tuple[bool, list[str]]:
    """
    Runs a command timing out right away, which killing doesn't end, like one in uninterruptible
    sleep, faked. Returns whether it finished and what was logged when it got waited for.
    """
    started: list[subprocess.Popen[str]] = []
    logged_on_waiting: list[str] = []

    def hard_to_kill(process: subprocess.Popen[str]) -> None:
        started.append(process)

        def wait(timeout: float | None = None) -> int:
            assert timeout is not None, "waiting for the killed command for good"
            if not logged_on_waiting:
                logged_on_waiting.extend(caplog.messages)
            raise subprocess.TimeoutExpired(process.args, timeout)

        monkeypatch.setattr(process, "wait", wait)

    try:
        finished = run_in_subprocess(
            args=["sleep", "60"],
            input_="",
            env=None,
            description="executing script",
            logger=_LOGGER,
            timeout=0,
            on_start=hard_to_kill,
        )
    finally:
        monkeypatch.undo()
        for process in started:
            process.wait(timeout=30)  # gone in fact, once killed
    return finished, logged_on_waiting


def test_command_still_there_after_killing_it_is_left_behind(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    finished, _logged_on_waiting = _run_command_hard_to_kill(monkeypatch, caplog)

    assert (finished, caplog.messages) == (
        False,
        [
            "executing script didn't finish within 0 s, killed it",
            (
                "executing script is still there 1.0 s after killing it, e.g. in uninterruptible "
                "sleep, going on without it"
            ),
        ],
    )


def test_killed_command_is_logged_before_waiting_for_it(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # So that the log tells which command hangs, even if it doesn't go away
    _finished, logged_on_waiting = _run_command_hard_to_kill(monkeypatch, caplog)

    assert logged_on_waiting == ["executing script didn't finish within 0 s, killed it"]


def _ends_soon(pid: int) -> bool:
    # Killing a process only makes it end once it gets to run, and its parent can be gone already.
    deadline = time.monotonic() + 30
    while _is_running(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)
    return True


def _is_running(pid: int) -> bool:
    try:
        # The state follows the command name in parentheses, see proc_pid_stat(5).
        state = Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0]
    except FileNotFoundError, ProcessLookupError:  # reaped before or while reading
        return False
    return state not in {"Z", "X"}  # A killed process can stay a zombie until its parent reaps it.


def test_runner_kills_a_command_not_finishing_within_its_timeout(
    caplog: pytest.LogCaptureFixture,
) -> None:
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), command_timeout=_SHORT_TIMEOUT)
    action_runner.start()

    _run_script_later(action_runner, "exec sleep 60")
    action_runner.stop(timeout=30)

    assert caplog.messages == ["executing script didn't finish within 0.1 s, killed it"]


def test_notification_isnt_killed_after_the_timeout_of_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Commands time out at once, so it would get killed before getting the notification.
    notification = tmp_path / "notification"
    notification.touch()  # empty unless Checkmk gets the notification
    put_on_path(monkeypatch, tmp_path / "bin", "cmk", f"cat > {shlex.quote(str(notification))}")
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), command_timeout=0)
    action_runner.start()

    _notify_about_an_event(action_runner)
    action_runner.stop(timeout=30)

    forwarded = notification.read_text().splitlines()
    assert (caplog.messages, "SERVICEOUTPUT=disk full" in forwarded) == ([], True)


def test_notification_not_finishing_within_its_timeout_is_killed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # Checkmk hanging while notifying
    put_on_path(monkeypatch, tmp_path / "bin", "cmk", "exec sleep 60")
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), notification_timeout=_SHORT_TIMEOUT)
    action_runner.start()

    _notify_about_an_event(action_runner)
    action_runner.stop(timeout=30)

    assert caplog.messages == [
        "forwarding notification for event 1 to Checkmk didn't finish within 0.1 s, killed it"
    ]


def _notify_about_an_event(action_runner: ActionRunner) -> None:
    core = FakeConnection()
    core.notifications_enabled = True
    do_notify(
        HostConfig(_LOGGER, core),
        _LOGGER,
        core,
        new_event(ec.Event(id=1, state=2, sl=0, text="disk full")),
        action_runner=action_runner,
    )


def test_script_action_is_recorded_in_the_history_once_it_has_run(
    settings: ec.Settings, config: Config
) -> None:
    history = RecordingHistory()
    # Not started yet, so that the command stays pending until the runner starts
    action_runner = ActionRunner(_LOGGER, history)
    _trigger_script_action(action_runner, settings, config, "true")
    whats_while_pending = history.whats

    action_runner.start()
    action_runner.stop(timeout=30)

    assert (whats_while_pending, history.whats) == ([], ["SCRIPT"])


def test_script_action_is_recorded_in_the_history_used_once_it_has_run(
    settings: ec.Settings, config: Config
) -> None:
    # Like after a reload, which closes the previous history afterwards
    previous_history = RecordingHistory()
    history = RecordingHistory()
    # Not started yet, so that the command stays pending until the runner starts
    action_runner = ActionRunner(_LOGGER, previous_history)
    _trigger_script_action(action_runner, settings, config, "true")

    action_runner.use_history(history)
    action_runner.start()
    action_runner.stop(timeout=30)

    assert (previous_history.whats, history.whats) == ([], ["SCRIPT"])


def test_killed_script_action_is_not_recorded_in_the_history(
    settings: ec.Settings, config: Config
) -> None:
    history = RecordingHistory()
    action_runner = ActionRunner(_LOGGER, history, command_timeout=_SHORT_TIMEOUT)
    action_runner.start()

    _trigger_script_action(action_runner, settings, config, "exec sleep 60")
    action_runner.stop(timeout=30)

    assert history.whats == []


def test_script_action_killed_on_stopping_is_not_recorded_in_the_history(
    tmp_path: Path, settings: ec.Settings, config: Config
) -> None:
    ready = tmp_path / "ready"
    history = RecordingHistory()
    action_runner = ActionRunner(_LOGGER, history)
    action_runner.start()
    _trigger_script_action(
        action_runner, settings, config, f"touch {shlex.quote(str(ready))}; exec sleep 60"
    )
    wait_until_exists(ready)

    action_runner.stop(timeout=0.1)
    action_runner.stop(timeout=30)  # i.e. wait for it to handle the killed command

    assert history.whats == []


def test_dropped_script_action_is_not_recorded_in_the_history(
    settings: ec.Settings, config: Config
) -> None:
    history = RecordingHistory()
    # Not started yet, so that the 1st command stays pending
    action_runner = ActionRunner(_LOGGER, history, max_pending=1)
    _run_script_later(action_runner, "true")

    _trigger_script_action(action_runner, settings, config, "true")
    action_runner.start()
    action_runner.stop(timeout=30)

    assert history.whats == []


def test_script_action_is_recorded_with_the_event_as_it_was_when_triggered(
    settings: ec.Settings, config: Config
) -> None:
    history = RecordingHistory()
    # Not started yet, so that the command stays pending until the runner starts
    action_runner = ActionRunner(_LOGGER, history)
    event = new_event(ec.Event(id=1, text="disk full"))
    _trigger_script_action(action_runner, settings, config, "true", event=event)

    event["comment"] = "taken care of"  # like an UPDATE command meanwhile
    action_runner.start()
    action_runner.stop(timeout=30)

    assert [event["comment"] for _what, event in history.entries] == [""]


class _HistoryRecordingDetails(RecordingHistory):
    """Records also who did what, with which additional information"""

    def __init__(self) -> None:
        super().__init__()
        self.details: list[tuple[HistoryWhat, str, str]] = []

    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        super().add(event, what, who, addinfo)
        self.details.append((what, who, addinfo))


def test_email_action_is_recorded_in_the_history_once_sent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, settings: ec.Settings, config: Config
) -> None:
    put_on_path(monkeypatch, tmp_path / "bin", "mail", "cat >/dev/null")
    history = _HistoryRecordingDetails()
    # Not started yet, so that the command stays pending until the runner starts
    action_runner = ActionRunner(_LOGGER, history)
    _trigger_action(action_runner, settings, config, _EMAIL_ACTION)
    details_while_pending = list(history.details)

    action_runner.start()
    action_runner.stop(timeout=30)

    assert (details_while_pending, history.details) == (
        [],
        [("EMAIL", "harry", "admins@example.com|EC")],
    )


class _HistoryFailingToAdd(RecordingHistory):
    @override
    def add(self, event: Event, what: HistoryWhat, who: str = "", addinfo: str = "") -> None:
        raise OSError("disk full")


def test_runner_logs_failing_to_record_an_action_and_runs_the_next_command(
    tmp_path: Path, settings: ec.Settings, config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    output = tmp_path / "output"
    action_runner = ActionRunner(_LOGGER, _HistoryFailingToAdd())
    action_runner.start()

    _trigger_script_action(action_runner, settings, config, "true")
    _run_script_later(action_runner, f"printf 2 > {shlex.quote(str(output))}")
    action_runner.stop(timeout=30)

    assert (caplog.messages, output.read_text()) == (
        ['Error after executing script of action "Open a ticket" on event 1'],
        "2",
    )


def test_script_action_is_logged_with_its_action_and_event(
    settings: ec.Settings, config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    # The runner logs it later, maybe after many other commands.
    caplog.set_level(logging.INFO)
    action_runner = ActionRunner(_LOGGER, RecordingHistory())
    action_runner.start()

    _trigger_script_action(action_runner, settings, config, "true")
    action_runner.stop(timeout=30)

    assert caplog.messages == ['executing script of action "Open a ticket" on event 1 succeeded']


def test_dropped_email_action_is_logged_with_its_action_and_event(
    settings: ec.Settings, config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    # Not started, so that the 1st command stays pending
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), max_pending=1)
    _run_script_later(action_runner, "true")

    _trigger_action(action_runner, settings, config, _EMAIL_ACTION)

    assert caplog.messages == [
        'Not sending email of action "Mail the admins" on event 1, as too many actions are pending'
    ]


_EMAIL_ACTION = EMailAction(
    id="mail",
    title="Mail the admins",
    hidden=False,
    disabled=False,
    action=("email", EMailActionConfig(to="admins@example.com", subject="EC", body="$TEXT$")),
)


def _trigger_script_action(
    action_runner: ActionRunner,
    settings: ec.Settings,
    config: Config,
    script: str,
    *,
    event: Event | None = None,
) -> None:
    action = ScriptAction(
        id="ticket",
        title="Open a ticket",
        hidden=False,
        disabled=False,
        action=("script", ScriptActionConfig(script=script)),
    )
    _trigger_action(action_runner, settings, config, action, event=event)


def _trigger_action(
    action_runner: ActionRunner,
    settings: ec.Settings,
    config: Config,
    action: Action,
    *,
    event: Event | None = None,
) -> None:
    """Triggers the action on the given event, by default a new one with ID 1, by user harry"""
    do_event_action(
        settings,
        config,
        _LOGGER,
        StatusTableEvents.columns,
        action,
        new_event(ec.Event(id=1, text="disk full")) if event is None else event,
        "harry",
        action_runner=action_runner,
    )


def test_runner_runs_the_commands_one_after_another(
    tmp_path: Path, action_runner: ActionRunner
) -> None:
    output = tmp_path / "output"

    # Running at the same time, the 2nd command would write first.
    _run_script_later(action_runner, f"sleep 0.1; printf 1 >> {shlex.quote(str(output))}")
    _run_script_later(action_runner, f"printf 2 >> {shlex.quote(str(output))}")
    action_runner.stop(timeout=30)

    assert output.read_text() == "12"


def test_runner_drops_commands_beyond_the_pending_ones_with_an_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    output = tmp_path / "output"
    # Not started yet, so that the 1st command stays pending
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), max_pending=1)
    _run_script_later(action_runner, f"printf 1 >> {shlex.quote(str(output))}")

    _run_script_later(action_runner, f"printf 2 >> {shlex.quote(str(output))}")
    logged = list(caplog.messages)  # without the number of dropped commands logged on stopping
    action_runner.start()
    action_runner.stop(timeout=30)

    assert (logged, output.read_text()) == (
        ["Not executing script, as too many actions are pending"],
        "1",
    )


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _dropping_runner(clock: _Clock) -> ActionRunner:
    """A runner which drops every further command, as the 1st one stays pending: It's not started."""
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), max_pending=1, clock=clock)
    _run_script_later(action_runner, "true")
    return action_runner


def test_runner_dropping_commands_which_keeps_happening_reminds_of_it_once_a_minute(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = _Clock()
    action_runner = _dropping_runner(clock)
    _run_script_later(action_runner, "true")
    caplog.clear()

    for now in (30.0, 60.0, 90.0, 120.0):
        clock.now = now
        _run_script_later(action_runner, "true")

    assert caplog.messages == [
        "Still too many actions are pending, 3 dropped so far",
        "Still too many actions are pending, 5 dropped so far",
    ]


def test_runner_taking_commands_again_logs_how_many_it_dropped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    action_runner = _dropping_runner(_Clock())
    _run_script_later(action_runner, "true")
    _run_script_later(action_runner, "true")
    action_runner.start()
    try:
        _wait_until_finished(action_runner)  # i.e. until there is room again
        caplog.clear()

        _run_script_later(action_runner, "true")
    finally:
        action_runner.stop(timeout=30)

    assert caplog.messages == ["Taking actions again, 2 dropped as too many were pending"]


def test_runner_kept_at_its_limit_logs_the_dropped_commands_as_one_series(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    running = tmp_path / "running"
    released = tmp_path / "released"
    # Not started yet, so that the commands stay pending, and then the 1st one waits for release
    action_runner = ActionRunner(_LOGGER, RecordingHistory(), max_pending=4, clock=_Clock())
    _run_script_later(
        action_runner,
        f"touch {shlex.quote(str(running))}; "
        f"until [ -e {shlex.quote(str(released))} ]; do sleep 0.01; done",
    )
    for _ in range(4):  # the last one dropped
        _run_script_later(action_runner, "true")
    action_runner.start()
    try:
        wait_until_exists(running)  # i.e. the 1st one isn't pending anymore

        # Like a steady overload: Once one has run, the next one is taken, the one after dropped.
        _run_script_later(action_runner, "true")
        _run_script_later(action_runner, "true")
        logged = list(caplog.messages)  # without the number of dropped commands logged on stopping
    finally:
        released.touch()
        action_runner.stop(timeout=30)

    assert logged == ["Not executing script, as too many actions are pending"]


def test_runner_taking_a_command_which_mustnt_be_dropped_goes_on_dropping_the_others(
    caplog: pytest.LogCaptureFixture,
) -> None:
    action_runner = _dropping_runner(_Clock())
    _run_script_later(action_runner, "true")
    caplog.clear()

    # Taken, although too many are pending, which doesn't end dropping the others
    action_runner.run(
        args=["/bin/sh"],
        input_="true",
        env=None,
        description="executing script",
        logger=_LOGGER,
        droppable=False,
    )
    _run_script_later(action_runner, "true")

    # The pending 1st command and the one taken, but no further ones logged as dropped
    assert (action_runner.unfinished(), caplog.messages) == (2, [])


def test_runner_stopping_while_dropping_commands_logs_how_many_it_dropped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    action_runner = _dropping_runner(_Clock())
    _run_script_later(action_runner, "true")
    _run_script_later(action_runner, "true")
    caplog.clear()

    action_runner.stop(timeout=30)

    assert caplog.messages == [
        "Stopping after dropping actions, 2 dropped as too many were pending"
    ]


def _wait_until_finished(action_runner: ActionRunner) -> None:
    deadline = time.monotonic() + 30
    while action_runner.unfinished():
        assert time.monotonic() < deadline, "commands still unfinished"
        time.sleep(0.01)


def test_runner_logs_a_command_it_cannot_run_and_runs_the_next_one(
    tmp_path: Path, action_runner: ActionRunner, caplog: pytest.LogCaptureFixture
) -> None:
    output = tmp_path / "output"

    action_runner.run(
        args=[str(tmp_path / "missing")],
        input_="",
        env=None,
        description="executing script",
        logger=_LOGGER,
    )
    _run_script_later(action_runner, f"printf 2 > {shlex.quote(str(output))}")
    action_runner.stop(timeout=30)

    assert (caplog.messages, output.read_text()) == (["Error while executing script"], "2")


def test_stopping_runner_kills_a_hanging_command_after_the_timeout(
    tmp_path: Path, action_runner: ActionRunner, caplog: pytest.LogCaptureFixture
) -> None:
    pid_file = tmp_path / "pid"
    ready = tmp_path / "ready"
    # Hanging, like the process it started, until killed
    _run_script_later(
        action_runner,
        f"sleep 60 >/dev/null 2>&1 & echo $! > {shlex.quote(str(pid_file))}; "
        f"touch {shlex.quote(str(ready))}; wait",
    )
    wait_until_exists(ready)

    try:
        action_runner.stop(timeout=0.1)
        ended = _ends_soon(int(pid_file.read_text()))
    finally:
        with suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)
    action_runner.stop(timeout=30)  # i.e. wait for it to log the killed command

    assert (ended, caplog.messages) == (
        True,
        [
            (
                "Not waiting any longer for actions still running or pending after 0.1 s, killing "
                "or dropping the 1 unfinished ones"
            ),
            "executing script got killed by signal 9",
        ],
    )


def test_stopping_runner_drops_the_pending_commands_after_the_timeout(
    tmp_path: Path, action_runner: ActionRunner, caplog: pytest.LogCaptureFixture
) -> None:
    ready = tmp_path / "ready"
    output = tmp_path / "output"
    _run_script_later(action_runner, f"touch {shlex.quote(str(ready))}; exec sleep 60")
    _run_script_later(action_runner, f"printf 2 > {shlex.quote(str(output))}")
    wait_until_exists(ready)

    action_runner.stop(timeout=0.1)
    action_runner.stop(timeout=30)  # i.e. wait for it to handle the pending command

    assert (action_runner.unfinished(), output.exists(), caplog.messages[0]) == (
        0,
        False,
        (
            "Not waiting any longer for actions still running or pending after 0.1 s, killing or "
            "dropping the 2 unfinished ones"
        ),
    )


class _EnvironmentHeldUp(Mapping[str, str]):
    """The environment of a command, holding up its start until released"""

    def __init__(self) -> None:
        self.being_read = threading.Event()
        self.released = threading.Event()

    @override
    def __getitem__(self, key: str) -> str:
        return os.environ[key]

    @override
    def __iter__(self) -> Iterator[str]:
        self.being_read.set()
        self.released.wait(timeout=30)
        return iter(os.environ)

    @override
    def __len__(self) -> int:
        return len(os.environ)


def test_command_starting_once_stopping_runner_gave_up_waiting_is_killed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    action_runner = ActionRunner(_LOGGER, RecordingHistory())
    action_runner.start()
    environment = _EnvironmentHeldUp()
    action_runner.run(
        args=["/bin/sh"],
        input_="exec sleep 60",
        env=environment,
        description="executing script",
        logger=_LOGGER,
    )
    assert environment.being_read.wait(timeout=30), "the command didn't start"

    # Gives up right before the command starts, so there's no process to kill yet.
    action_runner.stop(timeout=0)
    environment.released.set()
    action_runner.stop(timeout=30)  # i.e. wait for it to handle the killed command

    assert caplog.messages == [
        (
            "Not waiting any longer for actions still running or pending after 0 s, killing or "
            "dropping the 1 unfinished ones"
        ),
        "executing script got killed by signal 9",
    ]
