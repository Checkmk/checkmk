#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import os
import queue
import select
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from logging import Logger
from typing import NamedTuple

from cmk.ccc.log import VERBOSE
from cmk.events import event_context

from .config import Action, Config, EMailActionConfig, Rule, ScriptActionConfig
from .core_queries import Connection, query_contactgroups_members, query_status_enable_notifications
from .event import Event
from .history import History
from .host_config import HostConfig
from .settings import Settings


class ECEventContext(event_context.EventContext, total=False):
    """The keys "found" in cmk.ec

    Not sure if subclassing EventContext is the right call...
    Feel free to merge if you feel like doing it.
    """

    EC_CONTACT: str
    EC_CONTACT_GROUPS: str
    EC_MATCH_GROUPS: str
    EC_ORIG_HOST: str
    EC_OWNER: str
    EC_PHASE: str
    EC_PID: str
    HOSTADDRESS: str
    HOSTALIAS: str
    HOSTDOWNTIME: str
    LASTSERVICESTATEID: str
    NOTIFICATIONAUTHOR: str
    NOTIFICATIONAUTHORALIAS: str
    NOTIFICATIONAUTHORNAME: str
    SERVICEACKAUTHOR: str
    SERVICEACKCOMMENT: str
    SERVICEPERFDATA: str
    SERVICEPROBLEMID: str
    SERVICESTATEID: str
    SERVICE_EC_CONTACT: str
    SERVICE_SL: str

    # Dynamically added:
    # HOST_*: str  #  custom_variables


# .
#   .--Actions-------------------------------------------------------------.
#   |                     _        _   _                                   |
#   |                    / \   ___| |_(_) ___  _ __  ___                   |
#   |                   / _ \ / __| __| |/ _ \| '_ \/ __|                  |
#   |                  / ___ \ (__| |_| | (_) | | | \__ \                  |
#   |                 /_/   \_\___|\__|_|\___/|_| |_|___/                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Global functions for executing rule actions like sending emails and  |
#   | executing scripts.                                                   |
#   '----------------------------------------------------------------------'

_ContactgroupName = str


def event_has_opened(
    settings: Settings,
    config: Config,
    logger: Logger,
    connection: Connection,
    host_config: HostConfig,
    event_columns: Iterable[tuple[str, object]],
    rule: Rule,
    event: Event,
    *,
    action_runner: ActionRunner,
) -> None:
    """
    Prepare for events with a limited lifetime. This time starts
    when the event enters the open state or acked state.
    """
    if "livetime" in rule:
        livetime, phases = rule["livetime"]
        event["live_until"] = time.time() + livetime
        event["live_until_phases"] = phases

    if rule.get("actions_in_downtime", True) is False and event["host_in_downtime"]:
        logger.info(
            "Skip actions for event %(event_id)d: Host is in downtime",
            {"event_id": event["id"]},
        )
        return

    do_event_actions(
        settings,
        config,
        logger,
        connection,
        host_config,
        event_columns,
        rule.get("actions", []),
        event,
        is_cancelling=False,
        action_runner=action_runner,
    )


def do_event_actions(
    settings: Settings,
    config: Config,
    logger: Logger,
    connection: Connection,
    host_config: HostConfig,
    event_columns: Iterable[tuple[str, object]],
    actions: Iterable[str],
    event: Event,
    is_cancelling: bool,
    *,
    action_runner: ActionRunner,
) -> None:
    """Execute a list of actions on an event that has just been opened or cancelled."""
    table = config["action"]
    for aname in actions:
        if aname == "@NOTIFY":
            do_notify(
                host_config,
                logger,
                connection,
                event,
                is_cancelling=is_cancelling,
                action_runner=action_runner,
            )
        elif action := table.get(aname):
            logger.info(
                'triggering action "%(title)s" on event %(event_id)s',
                {"title": action["title"], "event_id": event["id"]},
            )
            do_event_action(
                settings,
                config,
                logger,
                event_columns,
                action,
                event,
                "",
                action_runner=action_runner,
            )
        else:
            logger.info(
                'undefined action "%(action_name)s", must be one of %(known_actions)s',
                {"action_name": aname, "known_actions": ", ".join(table.keys())},
            )


def do_event_action(
    settings: Settings,
    config: Config,
    logger: Logger,
    event_columns: Iterable[tuple[str, object]],
    action: Action,
    event: Event,
    user: str,
    *,
    action_runner: ActionRunner,
) -> None:
    action_id = action["id"]
    if action["disabled"]:
        logger.info("Skipping disabled action %(action_id)s.", {"action_id": action_id})
        return
    try:
        act = action["action"]
        # For the log messages about its command, which runs later
        of_action = f'of action "{action["title"]}" on event {event["id"]}'
        if act[0] == "email":
            _do_email_action(
                config,
                logger,
                event_columns,
                act[1],
                event,
                user,
                action_runner,
                description=f"sending email {of_action}",
            )
        elif act[0] == "script":
            _do_script_action(
                logger,
                event_columns,
                act[1],
                action_id,
                event,
                user,
                action_runner,
                description=f"executing script {of_action}",
            )
        else:
            # TODO: Really parse the config, then this can't happen
            logger.error(  # type: ignore[unreachable]
                "Cannot execute action %(action_id)s: invalid action type %(action_type)s",
                {"action_id": action_id, "action_type": act[0]},
            )

    except Exception:
        if settings.options.debug:
            raise
        logger.exception("Error during execution of action %(action_id)s", {"action_id": action_id})


def _do_email_action(
    config: Config,
    logger: Logger,
    event_columns: Iterable[tuple[str, object]],
    action_config: EMailActionConfig,
    event: Event,
    user: str,
    action_runner: ActionRunner,
    *,
    description: str,
) -> None:
    to = _prepare_text(action_config["to"], event_columns, event)
    subject = _prepare_text(action_config["subject"], event_columns, event)
    body = _prepare_text(action_config["body"], event_columns, event)
    # Recorded once sent, with the event as it is now
    recorded = event.copy()
    _send_email(
        config,
        to=to,
        subject=subject,
        body=body,
        logger=logger,
        action_runner=action_runner,
        description=description,
        on_finished=lambda history: history.add(recorded, "EMAIL", user, f"{to}|{subject}"),
    )


def _do_script_action(
    logger: Logger,
    event_columns: Iterable[tuple[str, object]],
    action_config: ScriptActionConfig,
    action_id: str,
    event: Event,
    user: str,
    action_runner: ActionRunner,
    *,
    description: str,
) -> None:
    # Recorded once it has run, with the event as it is now
    recorded = event.copy()
    _execute_script(
        event_columns,
        _escape_null_bytes(action_config["script"]),
        event,
        logger,
        action_runner,
        description=description,
        on_finished=lambda history: history.add(recorded, "SCRIPT", user, action_id),
    )


def _prepare_text(text: str, event_columns: Iterable[tuple[str, object]], event: Event) -> str:
    return _escape_null_bytes(_substitute_event_tags(text, event_columns, event))


def _escape_null_bytes(s: str) -> str:
    return s.replace("\000", "\\000")


def _substitute_event_tags(
    text: str, event_columns: Iterable[tuple[str, object]], event: Event
) -> str:
    for key, value in _get_event_tags(event_columns, event).items():
        text = text.replace(f"${key.upper()}$", value)
    return text


# How long the output of a killed command may stay open, e.g. by a process started with setsid
_OUTPUT_TIMEOUT_AFTER_KILLING = 1.0  # seconds

# How long a finished or killed command may take to go away: Uninterruptible sleep delays killing.
_EXIT_TIMEOUT = 1.0  # seconds


def run_in_subprocess(
    *,
    args: Sequence[str],
    input_: str,
    env: Mapping[str, str] | None,
    description: str,
    logger: Logger,
    timeout: float,
    clock: Callable[[], float] = time.monotonic,
    on_start: Callable[[subprocess.Popen[str]], None] | None = None,
) -> bool:
    """
    Runs the command and logs its result. At the timeout, it kills the command with the processes it
    started, or just these if they keep its output open, and leaves behind what doesn't go away.
    Returns whether the command finished, whatever its exit code. Only tests pass a clock.
    """
    deadline = clock() + timeout
    # In a session of its own, so that killing its process group kills just its processes
    process = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        close_fds=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    )
    try:
        try:
            if on_start is not None:
                on_start(process)
            if (output := _output_by_deadline(process, input_, deadline, clock)) is None:
                # Unless it has finished, maybe leaving processes keeping its output open
                timed_out = not _has_exited(process)
                left_output_open = not timed_out and _output_kept_open(process)
                # Logged right away, in case it doesn't go away
                if timed_out:
                    _kill_process_group(process)
                    logger.error(
                        "%(description)s didn't finish within %(timeout)s s, killed it",
                        {"description": description, "timeout": timeout},
                    )
                elif left_output_open:
                    _kill_process_group(process)
                    logger.error(
                        "%(description)s left processes keeping its output open after "
                        "%(timeout)s s, killed those in its process group",
                        {"description": description, "timeout": timeout},
                    )
                output = _rest_of_output(process)
            else:
                timed_out = left_output_open = False
        except BaseException:
            # Like subprocess.run() does
            _kill_process_group(process)
            raise
    finally:
        # Unlike leaving a with statement, without waiting for good
        gone = _close_and_reap(process)
    if not gone:
        logger.error(
            "%(description)s is still there %(timeout)s s after killing it, e.g. in uninterruptible "
            "sleep, going on without it",
            {"description": description, "timeout": _EXIT_TIMEOUT},
        )
    elif not timed_out:
        if process.returncode < 0:
            logger.error(
                "%(description)s got killed by signal %(signal)d",
                {"description": description, "signal": -process.returncode},
            )
        elif process.returncode:
            logger.error(
                "%(description)s failed with exit code %(returncode)d",
                {"description": description, "returncode": process.returncode},
            )
        elif not left_output_open:
            logger.info("%(description)s succeeded", {"description": description})
            return True
    for line in output.splitlines():
        logger.error("  output: %(line)s", {"line": line})
    return gone and not timed_out and process.returncode >= 0


def _has_exited(process: subprocess.Popen[str]) -> bool:
    """Tells whether the process has exited, without reaping it, so that its ID stays taken"""
    if process.returncode is not None:  # reaped already
        return True
    return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def _output_kept_open(process: subprocess.Popen[str]) -> bool:
    """Tells whether processes still keep the output of the process open"""
    if process.stdout is None or process.stdout.closed:  # read up to its end already
        return False
    poller = select.poll()
    poller.register(process.stdout, select.POLLIN)
    # A pipe without writers reports a hangup, even with output left in it.
    return not any(events & select.POLLHUP for _fd, events in poller.poll(0))


def _kill_process_group(process: subprocess.Popen[str]) -> None:
    """Kills the process together with the processes it started, i.e. its process group"""
    # Unless it has been reaped, which frees its ID for another process group
    if process.returncode is None:
        with contextlib.suppress(ProcessLookupError):  # all of them gone in the meantime
            os.killpg(process.pid, signal.SIGKILL)


def _close_and_reap(process: subprocess.Popen[str]) -> bool:
    """
    Closes the pipes to the process and reaps it, but only within _EXIT_TIMEOUT. Returns whether
    it's gone. If not, the subprocess module reaps it later.
    """
    for pipe in (process.stdout, process.stderr, process.stdin):
        if pipe is not None:
            # Flushing its input fails if it's gone.
            with contextlib.suppress(OSError):
                pipe.close()
    try:
        process.wait(timeout=_EXIT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False
    return True


def _output_by_deadline(
    process: subprocess.Popen[str], input_: str, deadline: float, clock: Callable[[], float]
) -> str | None:
    """The output of the process once it has finished, None if it hasn't by the deadline"""
    input_left: str | None = input_
    while True:
        try:
            output, _ = process.communicate(input_left, timeout=max(0.0, deadline - clock()))
            return output
        except subprocess.TimeoutExpired:
            # With the real clock, it's the deadline already.
            if clock() >= deadline:
                return None
            # Communicating again loses no output, but takes no input.
            input_left = None


def _rest_of_output(process: subprocess.Popen[str]) -> str:
    """The output of the process after the deadline, once it has finished or got killed"""
    try:
        # Communicating again loses no output.
        output, _ = process.communicate(timeout=_OUTPUT_TIMEOUT_AFTER_KILLING)
        return output
    except subprocess.TimeoutExpired as e:
        # The output so far, as bytes even in text mode
        return (e.output or b"").decode("utf-8", errors="replace")


# The least time between two reminders of commands being dropped
_DROP_REMINDER_INTERVAL = 60.0  # seconds


class _Command(NamedTuple):
    args: Sequence[str]
    input_: str
    env: Mapping[str, str] | None
    description: str
    logger: Logger
    timeout: float
    on_finished: Callable[[History], None] | None


class ActionRunner:
    """
    Runs the commands of actions one after another in a thread of its own, killing those which don't
    finish within their timeout

    Running them in the threads triggering them could hang the EC: A script writing into the full
    event pipe waits for the event server, which may wait for the lock held by the trigger.
    """

    def __init__(
        self,
        logger: Logger,
        history: History,
        *,
        max_pending: int = 2000,
        command_timeout: float = 60.0,
        notification_timeout: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._logger = logger
        # The history to record the actions in, see use_history(), and the lock for replacing it
        self._history = history
        self._history_lock = threading.Lock()
        # By default like the one of notification plug-ins
        self._command_timeout = command_timeout
        # Longer for notifications, as synchronous delivery runs the notification plug-ins one after
        # another, each with a timeout of a minute by default
        self._notification_timeout = notification_timeout
        # Bounded by run() for droppable commands, so that a flood of events can't take all memory
        self._max_pending = max_pending
        self._pending: queue.Queue[_Command | None] = queue.Queue()
        # A daemon thread, so that a hanging command can't keep the EC from terminating
        self._thread = threading.Thread(target=self._run_pending, name="ActionRunner", daemon=True)
        # The count of pending and running commands, the running process and whether stop() gave up
        self._unfinished = 0
        self._running: subprocess.Popen[str] | None = None
        self._stopped = False
        # The current series of dropped commands, see _log_dropped(). Only tests pass a clock.
        self._dropped = 0
        self._next_drop_reminder = 0.0
        self._clock = clock
        self._lock = threading.Lock()

    def start(self) -> None:
        """Starts running the commands, after daemonizing, which keeps only the forking thread"""
        self._thread.start()

    def run(
        self,
        *,
        args: Sequence[str],
        input_: str,
        env: Mapping[str, str] | None,
        description: str,
        logger: Logger,
        is_notification: bool = False,
        on_finished: Callable[[History], None] | None = None,
        droppable: bool = True,
    ) -> None:
        """
        Runs the command once the ones before it have finished, then calls the given function with
        the history, unless the command didn't finish. Drops it if droppable and too many commands
        are pending.
        """
        timeout = self._notification_timeout if is_notification else self._command_timeout
        command = _Command(args, input_, env, description, logger, timeout, on_finished)
        with self._lock:
            # Others put commands only while holding the lock, too.
            pending = self._pending.qsize()
            if droppable and pending >= self._max_pending:
                self._log_dropped(logger, description)
                return
            # Counted before the command can run
            self._unfinished += 1
            self._pending.put(command)
            # A series of dropped ones ends only below half the limit, as otherwise a steady
            # overload would log its end and a new start for each command taken.
            if pending <= self._max_pending // 2 and (dropped := self._end_dropped()):
                logger.warning(
                    "Taking actions again, %(dropped)d dropped as too many were pending",
                    {"dropped": dropped},
                )

    # protected by self._lock
    def _log_dropped(self, logger: Logger, description: str) -> None:
        """
        Logs dropping a command, but of a series only the first one, a reminder at most every
        _DROP_REMINDER_INTERVAL and their number once it ends, so that a flood doesn't flood the log
        """
        self._dropped += 1
        now = self._clock()
        if self._dropped == 1:
            # Without a stack trace, which would tell nothing
            logger.error(
                "Not %(description)s, as too many actions are pending", {"description": description}
            )
        elif now >= self._next_drop_reminder:
            logger.error(
                "Still too many actions are pending, %(dropped)d dropped so far",
                {"dropped": self._dropped},
            )
        else:
            return
        self._next_drop_reminder = now + _DROP_REMINDER_INTERVAL

    # protected by self._lock
    def _end_dropped(self) -> int:
        """Ends the current series of dropped commands, returning their number"""
        dropped, self._dropped = self._dropped, 0
        return dropped

    def unfinished(self) -> int:
        """Returns how many commands are pending or running"""
        with self._lock:
            return self._unfinished

    def use_history(self, history: History) -> None:
        """
        Records the actions finishing from now on in the given history. Returns once the previous
        one is unused, so that the caller can close it.
        """
        with self._history_lock:
            self._history = history

    def stop(self, timeout: float) -> None:
        """
        Lets the pending commands run, but at most for the timeout. Then it kills the running one
        and drops the pending ones.
        """
        with self._lock:
            dropped = self._end_dropped()
        if dropped:
            self._logger.warning(
                "Stopping after dropping actions, %(dropped)d dropped as too many were pending",
                {"dropped": dropped},
            )
        if not self._thread.is_alive():
            return
        self._pending.put(None)
        self._thread.join(timeout)
        if not self._thread.is_alive():
            return
        # Before killing the running one, which the thread logs afterwards. One about to start gets
        # killed, too, see _set_running().
        self._logger.warning(
            "Not waiting any longer for actions still running or pending after %(timeout)s s, "
            "killing or dropping the %(unfinished)d unfinished ones",
            {"timeout": timeout, "unfinished": self.unfinished()},
        )
        with self._lock:
            self._stopped = True
            process = self._running
        if process is not None:
            _kill_process_group(process)

    def _run_pending(self) -> None:
        while (command := self._pending.get()) is not None:
            try:
                with self._lock:
                    stopped = self._stopped
                if not stopped:
                    self._run(command)
            finally:
                with self._lock:
                    self._unfinished -= 1
                    self._running = None

    def _run(self, command: _Command) -> None:
        try:
            finished = run_in_subprocess(
                args=command.args,
                input_=command.input_,
                env=command.env,
                description=command.description,
                logger=command.logger,
                timeout=command.timeout,
                on_start=self._set_running,
            )
        except Exception:
            command.logger.exception(
                "Error while %(description)s", {"description": command.description}
            )
            return
        if finished and command.on_finished is not None:
            try:
                with self._history_lock:
                    command.on_finished(self._history)
            except Exception:
                command.logger.exception(
                    "Error after %(description)s", {"description": command.description}
                )

    def _set_running(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._running = process
            stopped = self._stopped
        # Started after stop() gave up waiting, which then found no process to kill
        if stopped:
            _kill_process_group(process)


def _send_email(
    config: Config,
    *,
    to: str,
    subject: str,
    body: str,
    logger: Logger,
    action_runner: ActionRunner,
    description: str,
    on_finished: Callable[[History], None],
) -> None:
    args = ["mail", "-S", "sendcharsets=utf-8", "-s", subject, to]
    if config["debug_rules"]:
        logger.info("  Executing: %(command)s", {"command": " ".join(args)})
    action_runner.run(
        args=args,
        input_=body,
        env=None,
        description=description,
        logger=logger,
        on_finished=on_finished,
    )


def _execute_script(
    event_columns: Iterable[tuple[str, object]],
    body: str,
    event: Event,
    logger: Logger,
    action_runner: ActionRunner,
    *,
    description: str,
    on_finished: Callable[[History], None],
) -> None:
    action_runner.run(
        args=["/bin/bash"],
        input_=body,
        env=(
            os.environ
            | {
                "CMK_" + key.upper(): value  #
                for key, value in _get_event_tags(event_columns, event).items()
            }
        ),
        description=description,
        logger=logger,
        on_finished=on_finished,
    )


def _get_event_tags(
    event_columns: Iterable[tuple[str, object]],
    event: Event,
) -> dict[str, str]:
    substs: list[tuple[str, object]] = [
        (f"match_group_{nr + 1}", g) for nr, g in enumerate(event.get("match_groups", ()))
    ]

    for key, defaultvalue in event_columns:
        varname = key[6:]
        substs.append((varname, event.get(varname, defaultvalue)))

    def to_string(v: object) -> str:
        return v if isinstance(v, str) else str(v)

    return {
        key: " ".join(map(to_string, value)) if isinstance(value, tuple) else to_string(value)
        for key, value in substs
    }


# .
#   .--Notification--------------------------------------------------------.
#   |         _   _       _   _  __ _           _   _                      |
#   |        | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __           |
#   |        |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \          |
#   |        | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | |         |
#   |        |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  EC create Checkmk native notifications via cmk --notify.           |
#   '----------------------------------------------------------------------'

# Es fehlt:
# - Wenn CONTACTS fehlen, dann müssen in notify.py die Fallbackadressen
#   genommen werden.
# - Was ist mit Nagios als Core. Sendet der CONTACTS? Nein!!
#
# - Das muss sich in den Hilfetexten wiederspiegeln


def do_notify(
    host_config: HostConfig,
    logger: Logger,
    connection: Connection,
    event: Event,
    username: str | None = None,
    is_cancelling: bool = False,
    *,
    action_runner: ActionRunner,
    droppable: bool = True,
) -> None:
    """
    Creates a Checkmk Notification for a locally running Checkmk, even with too many actions
    pending unless it's droppable.

    We simulate a *service* notification.
    """
    if not _core_has_notifications_enabled(logger, connection):
        logger.info(
            "Notifications are currently disabled. Skipped notification for event %(event_id)d",
            {"event_id": event["id"]},
        )
        return

    context = _create_notification_context(
        host_config, event, username, is_cancelling, logger, connection
    )

    if logger.isEnabledFor(VERBOSE):
        logger.log(VERBOSE, "Sending notification via Check_MK with the following context:")
        for varname, value in sorted(context.items()):
            logger.log(VERBOSE, "  %(varname)-25s: %(value)s", {"varname": varname, "value": value})

    if context["HOSTDOWNTIME"] != "0":
        logger.info(
            "Host %(hostname)s is currently in scheduled downtime. "
            "Skipping notification of event %(event_id)s.",
            {"hostname": context["HOSTNAME"], "event_id": event["id"]},
        )
        return

    # Send notification context via stdin.
    context_string = "".join(
        "{}={}\n".format(varname, value.replace("\\", "\\\\").replace("\n", "\\n"))
        for (varname, value) in context.items()
        if isinstance(
            value, str
        )  # context is TypedDict which is dict[str, object], in fact it is dict[str, str]
    )

    action_runner.run(
        args=["cmk", "--notify", "stdin"],
        input_=context_string,
        env=None,
        description=f"forwarding notification for event {event['id']} to Checkmk",
        logger=logger,
        is_notification=True,
        droppable=droppable,
    )


def _create_notification_context(
    host_config: HostConfig,
    event: Event,
    username: str | None,
    is_cancelling: bool,
    logger: Logger,
    connection: Connection,
) -> ECEventContext:
    context = _base_notification_context(event, username, is_cancelling)
    _add_infos_from_monitoring_host(host_config, context, event)  # involves Livestatus query
    _add_contacts_from_rule(context, event, logger, connection)
    return context


def _base_notification_context(
    event: Event, username: str | None, is_cancelling: bool
) -> ECEventContext:
    rule_id = event["rule_id"]
    return ECEventContext(
        WHAT="SERVICE",
        CONTACTNAME="check-mk-notify",
        DATE=str(int(event["last"])),  # -> Event: Time
        MICROTIME=str(int(event["last"] * 1000000)),
        LASTSERVICESTATE=is_cancelling
        and "CRITICAL"
        or "OK",  # better assume OK, we have no transition information
        LASTSERVICESTATEID="2" if is_cancelling else "0",  # -> immer OK
        LASTSERVICEOK="0",  # 1.1.1970
        LASTSERVICESTATECHANGE=str(int(event["last"])),
        LONGSERVICEOUTPUT="",
        NOTIFICATIONAUTHOR="" if username is None else username,
        NOTIFICATIONAUTHORALIAS="" if username is None else username,
        NOTIFICATIONAUTHORNAME="" if username is None else username,
        NOTIFICATIONCOMMENT="",
        NOTIFICATIONTYPE="RECOVERY" if is_cancelling else "PROBLEM",
        SERVICEACKAUTHOR="",
        SERVICEACKCOMMENT="",
        SERVICEATTEMPT="1",
        SERVICECHECKCOMMAND="ec-internal" if rule_id is None else "ec-rule-" + rule_id,
        SERVICEDESC=event["application"] or "Event Console",
        SERVICENOTIFICATIONNUMBER="1",
        SERVICEOUTPUT=event["text"],
        SERVICEPERFDATA="",
        SERVICEPROBLEMID="ec-id-" + str(event["id"]),
        SERVICESTATE=_service_state_name(event["state"]),
        SERVICESTATEID=str(event["state"]),
        SERVICE_EC_CONTACT=event.get("owner", ""),
        SERVICE_SL=str(event["sl"]),
        SVC_SL=str(event["sl"]),
        # Some fields only found in EC notifications
        EC_ID=str(event["id"]),
        EC_RULE_ID="" if rule_id is None else rule_id,
        EC_PRIORITY=str(event["priority"]),
        EC_FACILITY=str(event["facility"]),
        EC_PHASE=event["phase"],
        EC_COMMENT=event.get("comment", ""),
        EC_OWNER=event.get("owner", ""),
        EC_CONTACT=event.get("contact", ""),
        EC_PID=str(event.get("pid", 0)),
        EC_MATCH_GROUPS="\t".join(event["match_groups"]),
        EC_CONTACT_GROUPS=" ".join(event.get("contact_groups") or []),
        EC_ORIG_HOST=event.get("orig_host", event["host"]),
    )


def _add_infos_from_monitoring_host(
    host_config: HostConfig, context: ECEventContext, event: Event
) -> None:
    """
    Note: "CONTACTS" is allowed to be missing in the context, cmk --notify will
    add the fallback contacts then.
    """

    def _add_artificial_context_info() -> None:
        context.update(
            {
                "HOSTNAME": event_context.HostName(event["host"]),
                "HOSTALIAS": event["host"],
                "HOSTADDRESS": event["ipaddress"],
                "HOSTTAGS": "",
                "HOSTDOWNTIME": "0",  # Non existing host cannot be in scheduled downtime ;-)
                "CONTACTS": "?",  # Will trigger using fallback contacts
                "SERVICECONTACTGROUPNAMES": "",
            }
        )

    core_host = event["core_host"]
    if not core_host:
        # Host not known in active monitoring. Create artificial host context
        # as good as possible.
        _add_artificial_context_info()
        return

    config = host_config.get_config_for_host(core_host)
    if config is None:
        _add_artificial_context_info()  # No config found - Host has vanished?
        return

    context.update(
        {
            "HOSTNAME": event_context.HostName(config.name),
            "HOSTALIAS": config.alias,
            "HOSTADDRESS": config.address,
            "HOSTTAGS": config.custom_variables.get("TAGS", ""),
            "CONTACTS": ",".join(config.contacts),
            "SERVICECONTACTGROUPNAMES": ",".join(config.contact_groups),
            "HOSTGROUPNAMES": ",".join(config.host_groups),
        }
    )

    # Add custom variables to the notification context
    for key, val in config.custom_variables.items():
        # TypedDict with dynamic keys... The typing we have is worth the suppression
        context[f"HOST_{key}"] = val  # type: ignore[literal-required]

    context["HOSTDOWNTIME"] = "1" if event["host_in_downtime"] else "0"


def _add_contacts_from_rule(
    context: ECEventContext,
    event: Event,
    logger: Logger,
    connection: Connection,
) -> None:
    """
    Add contact information from the rule, but only if the
    host is unknown or if contact groups in rule have precedence.
    """
    contact_groups = event.get("contact_groups")
    if (
        contact_groups is not None
        and event.get("contact_groups_notify")
        and (
            "CONTACTS" not in context
            or event.get("contact_groups_precedence", "host") != "host"
            or not event["core_host"]
        )
    ):
        _add_contact_information_to_context(context, contact_groups, logger, connection)


def _add_contact_information_to_context(
    context: ECEventContext,
    contact_groups: Iterable[_ContactgroupName],
    logger: Logger,
    connection: Connection,
) -> None:
    try:
        contact_names = query_contactgroups_members(connection, contact_groups)
    except Exception:
        logger.exception("Cannot get contact group members, assuming none:")
        contact_names = set()
    context["CONTACTS"] = ",".join(contact_names)
    context["SERVICECONTACTGROUPNAMES"] = ",".join(contact_groups)
    logger.log(
        VERBOSE,
        "Setting %(contact_count)d contacts %(contacts)s "
        "resulting from rule contact groups %(contact_groups)s",
        {
            "contact_count": len(contact_names),
            "contacts": ",".join(contact_names),
            "contact_groups": ",".join(contact_groups),
        },
    )


def _core_has_notifications_enabled(logger: Logger, connection: Connection) -> bool:
    try:
        return query_status_enable_notifications(connection)
    except Exception:
        logger.exception(
            "Cannot determine whether notifications are enabled in core, assuming YES."
        )
        return True


def _service_state_name(state_num: int) -> str:
    return {
        -1: "NODATA",
        0: "OK",
        1: "WARNING",
        2: "CRITICAL",
        3: "UNKNOWN",
    }.get(state_num, "")
