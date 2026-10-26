# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Commands in the guest's autologon console session.

Run-as spawns, COM services, SQL Server setup (which encrypts with the
user's DPAPI key) and Windows logins to SQL Server need the Administrator in
that session, not the guest agent's LocalSystem in session 0. A command gets
there as a one-shot scheduled task with the Administrator's password and
the elevated token.
"""

import contextlib
import os
import random
import re
import time

from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, GuestError, ps_quote

TASK_DIR = r"C:\Windows\Temp\qwin"
# schtasks' Last Result of a task that has not run yet (0x41303).
_NOT_RUN_YET = "267011"


class SessionError(VmError):
    """A session command that failed; log holds its output so far."""

    def __init__(self, message: str, log: str) -> None:
        super().__init__(message)
        self.log = log


def run_in_session(guest: Guest, command: str, timeout: float) -> str:
    """Runs command (cmd syntax) in the console session and returns its
    output. Fails if any step fails, the command exits non-zero, the task
    ends without its exit code (it never started, or was killed) or does not
    finish within timeout."""
    task = f"qwin-{os.getpid()}-{random.randrange(32768)}"
    path = rf"{TASK_DIR}\{task}"
    # The exit code goes to .rc in one move: a poll never sees it half written.
    script = "".join(
        f"{line}\r\n"
        for line in (
            "@echo off",
            f"call {command} > {path}.log 2>&1",
            f"(echo %ERRORLEVEL%) > {path}.rc.tmp",
            f"move /y {path}.rc.tmp {path}.rc > nul",
        )
    )
    try:
        guest.powershell(
            f"New-Item -ItemType Directory -Force -Path {ps_quote(TASK_DIR)} | Out-Null"
        )
        guest.write(f"{path}.cmd", script.encode())
    except GuestError as e:
        raise SessionError(f"copying the task script into the guest failed: {e}", "") from None
    try:
        return _run(guest, command, task, path, timeout)
    finally:
        _drop(guest, task, path)


def _run(guest: Guest, command: str, task: str, path: str, timeout: float) -> str:
    try:
        guest.run(
            ["schtasks.exe", "/create", "/tn", task, "/tr", f"{path}.cmd", "/sc", "once"]
            + ["/st", "00:00", "/ru", guest.user, "/rp", guest.password, "/it", "/rl", "highest"]
            + ["/f"]
        )
    except GuestError as e:
        raise SessionError(
            f"schtasks /create failed (no console session for /it?): {e}", ""
        ) from None
    try:
        guest.run(["schtasks.exe", "/run", "/tn", task])
    except GuestError as e:
        raise SessionError(f"schtasks /run failed: {e}", "") from None
    deadline = time.monotonic() + timeout
    while not guest.exists(f"{path}.rc"):
        guest.check()
        # .rc again: the task may have finished since.
        if (result := _ended(guest, task)) is not None and not guest.exists(f"{path}.rc"):
            raise SessionError(
                f"the task for '{command}' ended without an exit code ({result})",
                _partial_log(guest, path),
            )
        if time.monotonic() >= deadline:
            # The command holds its log open for writing until it ends, and
            # the guest agent cannot open a file that is open for writing.
            _end(guest, task)
            raise SessionError(
                f"'{command}' did not finish within {timeout:g} s", _partial_log(guest, path)
            )
        time.sleep(5)
    log = _log(guest, path)
    rc = guest.read(f"{path}.rc").decode(errors="replace").strip()
    if rc != "0":
        raise SessionError(f"'{command}' exited with {rc or 'an unknown status'}", log)
    return log


def _ended(guest: Guest, task: str) -> str | None:
    """The task's Last Result once it is Ready again after a run, else None."""
    info = guest.run(["schtasks.exe", "/query", "/tn", task, "/fo", "list", "/v"], check=False)
    last = re.search(r"^Last Result: *(\S+)", info.stdout, re.MULTILINE)
    if not re.search(r"^Status: *Ready", info.stdout, re.MULTILINE) or not last:
        return None
    return None if last[1] == _NOT_RUN_YET else f"Last Result: {last[1]}"


def _log(guest: Guest, path: str) -> str:
    """The command's output so far; none before the task has started."""
    if not guest.exists(f"{path}.log"):
        return ""
    return guest.read(f"{path}.log").decode(errors="replace").replace("\r", "")


def _partial_log(guest: Guest, path: str) -> str:
    """The output of a command that did not finish, or why it is missing:
    reading it must not hide why the command failed."""
    try:
        return _log(guest, path)
    except GuestError as e:
        return f"(its output could not be read: {e})"


def _end(guest: Guest, task: str) -> None:
    """Ends the task's process tree: schtasks /end ends only its cmd.exe and
    would leave the command it runs going. Best effort, as _drop."""
    with contextlib.suppress(GuestError):
        guest.powershell(
            "Get-CimInstance Win32_Process -Filter \"Name = 'cmd.exe'\""
            f" | Where-Object CommandLine -Like {ps_quote(f'*{task}.cmd*')}"
            " | ForEach-Object { taskkill.exe /f /t /pid $_.ProcessId }",
            check=False,
        )
        guest.run(["schtasks.exe", "/end", "/tn", task], check=False)


def _drop(guest: Guest, task: str, path: str) -> None:
    """Removes the task and its files, best effort: the command may have
    failed because the guest no longer answers, and the cleanup failing too
    must not replace that error."""
    _end(guest, task)
    with contextlib.suppress(GuestError):
        guest.run(["schtasks.exe", "/delete", "/tn", task, "/f"], check=False)
        guest.powershell(
            "Remove-Item -Force -ErrorAction Ignore -Path "
            + ", ".join(
                ps_quote(f"{path}{suffix}") for suffix in (".cmd", ".log", ".rc", ".rc.tmp")
            ),
            check=False,
        )
