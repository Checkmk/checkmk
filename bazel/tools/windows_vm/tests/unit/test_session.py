# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import override
from unittest.mock import Mock

import pytest
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, GuestError
from qemu_windows.qga import Qga
from qemu_windows.session import run_in_session, SessionError


@dataclass
class GuestState:
    """What the fake guest's scheduled tasks do: the command finishes after
    polls_until_done polls with exit code rc (None: never), and schtasks
    reports ended_status once it is Ready again. A command with
    log_held_open keeps its log unreadable until its process tree is ended,
    and log_unreadable makes it unreadable for good. Once vm_error has been
    raised, the guest runs no more commands."""

    rc: str | None = "0"
    log: str = ""
    polls_until_done: int = 1
    ended_status: str | None = None
    vm_error: VmError | None = None
    log_held_open: bool = False
    log_unreadable: bool = False
    tree_ended: bool = False
    dead: bool = False
    scripts: dict[str, bytes] = field(default_factory=dict)
    tasks: set[str] = field(default_factory=set)

    def check(self) -> None:
        if self.vm_error is not None:
            self.dead = True
            raise self.vm_error

    def run(self, argv: list[str]) -> str:
        if argv[:2] == ["schtasks.exe", "/create"]:
            self.tasks.add(argv[3])
        elif argv[:2] == ["schtasks.exe", "/delete"]:
            self.tasks.discard(argv[3])
        elif argv[:2] == ["schtasks.exe", "/query"]:
            return self.ended_status or "Status: Running\nLast Result: 267011\n"
        return ""

    def exists(self, path: str) -> bool:
        if path.endswith(".rc"):
            self.polls_until_done -= 1
            return self.polls_until_done <= 0 and self.rc is not None
        return path.endswith(".log")

    def powershell(self, script: str) -> None:
        if "taskkill.exe" in script:
            self.tree_ended = True

    def read(self, path: str) -> bytes:
        if path.endswith(".rc"):
            return f"{self.rc}\r\n".encode()
        if self.log_unreadable or (self.log_held_open and not self.tree_ended):
            raise GuestError(f"guest-file-open: {path}: being used by another process")
        return self.log.encode()


@dataclass(frozen=True)
class FakeGuest(Guest):
    state: GuestState = field(default_factory=GuestState)

    @override
    def run(
        self, argv: Sequence[str], *, check: bool = True, timeout: float = 3600.0
    ) -> subprocess.CompletedProcess[str]:
        self._alive()
        return subprocess.CompletedProcess(argv, 0, self.state.run(list(argv)), "")

    @override
    def powershell(
        self, script: str, *, check: bool = True, timeout: float = 3600.0
    ) -> subprocess.CompletedProcess[str]:
        self._alive()
        self.state.powershell(script)
        return subprocess.CompletedProcess(script, 0, "", "")

    def _alive(self) -> None:
        if self.state.dead:
            raise GuestError("guest-exec: the guest agent did not answer")

    @override
    def exists(self, path: str) -> bool:
        return self.state.exists(path)

    @override
    def read(self, remote: str) -> bytes:
        return self.state.read(remote)

    @override
    def write(self, remote: str, data: bytes) -> None:
        self.state.scripts[remote] = data


def fake_guest(state: GuestState) -> FakeGuest:
    return FakeGuest(Mock(spec=Qga), state.check, state=state)


@pytest.fixture(name="no_sleep")
def fixture_no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)


pytestmark = pytest.mark.usefixtures("no_sleep")


def test_output_is_returned_when_the_command_exits_zero() -> None:
    guest = fake_guest(GuestState(log="installed\n", polls_until_done=3))

    assert run_in_session(guest, "setup.exe", 60) == "installed\n"


def test_nonzero_exit_fails_with_the_commands_output() -> None:
    guest = fake_guest(GuestState(rc="3010", log="reboot needed\n"))

    with pytest.raises(SessionError, match="'setup.exe' exited with 3010") as error:
        run_in_session(guest, "setup.exe", 60)

    assert error.value.log == "reboot needed\n"


def test_task_that_ends_without_an_exit_code_fails() -> None:
    guest = fake_guest(
        GuestState(rc=None, ended_status="Status: Ready\nLast Result: -2147024894\n")
    )

    with pytest.raises(SessionError, match=r"ended without an exit code \(Last Result: -2147"):
        run_in_session(guest, "missing.exe", 60)


def test_command_that_outlasts_its_timeout_fails_with_its_output_so_far() -> None:
    guest = fake_guest(GuestState(rc=None, log="still installing\n", log_held_open=True))

    with pytest.raises(SessionError, match="did not finish within 0 s") as error:
        run_in_session(guest, "hang.exe", 0)

    assert error.value.log == "still installing\n"


def test_an_unreadable_log_does_not_hide_the_timeout() -> None:
    guest = fake_guest(GuestState(rc=None, log_unreadable=True))

    with pytest.raises(SessionError, match="did not finish within 0 s") as error:
        run_in_session(guest, "hang.exe", 0)

    assert error.value.log.startswith("(its output could not be read: ")


def test_a_dead_vm_ends_the_wait() -> None:
    guest = fake_guest(GuestState(rc=None, vm_error=VmError("QEMU has exited")))

    with pytest.raises(VmError, match="QEMU has exited"):
        run_in_session(guest, "setup.exe", 60)


def test_cleanup_on_a_dead_vm_keeps_the_vms_error() -> None:
    guest = fake_guest(GuestState(rc=None, vm_error=VmError("QEMU has exited")))

    with pytest.raises(VmError, match="QEMU has exited"):
        run_in_session(guest, "setup.exe", 60)


def test_task_is_deleted_from_the_guest_afterwards() -> None:
    guest = fake_guest(GuestState(rc="1"))

    with pytest.raises(SessionError):
        run_in_session(guest, "setup.exe", 60)

    assert guest.state.tasks == set()


def test_task_script_moves_the_exit_code_into_place_after_the_command() -> None:
    guest = fake_guest(GuestState())

    run_in_session(guest, "setup.exe /q", 60)

    ((remote, script),) = guest.state.scripts.items()
    path = remote.removesuffix(".cmd")
    assert script.decode().split("\r\n") == [
        "@echo off",
        f"call setup.exe /q > {path}.log 2>&1",
        f"(echo %ERRORLEVEL%) > {path}.rc.tmp",
        f"move /y {path}.rc.tmp {path}.rc > nul",
        "",
    ]
