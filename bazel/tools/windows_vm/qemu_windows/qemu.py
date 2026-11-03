# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType
from typing import Self

from qemu_windows import machine
from qemu_windows.errors import VmError
from qemu_windows.qmp import Qmp

# The VM states QEMU only leaves on a request. io-error: a full host disk
# (the IDE disk's werror=enospc), which qemu.log does not mention. shutdown:
# the guest powered off and -no-shutdown kept QEMU up.
_STOPPED = ("io-error", "internal-error", "shutdown")


class Qemu:
    """One QEMU running a test VM, from start() until quit().

    QEMU runs as a child with PR_SET_PDEATHSIG: if the caller dies (a Bazel
    timeout kills the test's process group, a SIGKILL skips its cleanup), so
    does the VM. It is never daemonized nor given a session of its own, which
    would leave the group. The signal follows the thread that started QEMU,
    so start it from the main thread.
    """

    def __init__(
        self, process: subprocess.Popen[bytes], log: Path, socket_dir: Path, qmp: Qmp
    ) -> None:
        self._process = process
        self._socket_dir = socket_dir
        self._qmp = qmp
        self.log = log
        # The guest agent's port and COM1 (machine.argv): sockets QEMU
        # listens on, one client at a time each.
        self.qga_socket = socket_dir / machine.QGA_CHARDEV
        self.console_socket = socket_dir / machine.CONSOLE_CHARDEV

    @classmethod
    def start(cls, argv: Sequence[str], workdir: Path, extra: Sequence[str] = ()) -> Self:
        """Starts QEMU with argv (machine.argv) and extra, its log in workdir."""
        workdir.mkdir(parents=True, exist_ok=True)
        # QMP takes `migrate exec:<command>`, the guest agent runs programs
        # as LocalSystem: socket files in a private directory, not abstract
        # sockets, which any local user could connect to. Under /tmp, not
        # $TMPDIR: socket paths end at 108 bytes.
        socket_dir = Path(tempfile.mkdtemp(prefix="qwin.", dir="/tmp"))  # nosec B108 # BNS:13b2c8
        socket_path = socket_dir / "qmp"
        chardevs = [
            arg
            for chardev in ("qmp", machine.QGA_CHARDEV, machine.CONSOLE_CHARDEV)
            for arg in (
                "-chardev",
                f"socket,id={chardev},path={socket_dir / chardev},server=on,wait=off",
            )
        ]
        log = workdir / "qemu.log"
        with log.open("wb") as out:
            process = subprocess.Popen(
                ["setpriv", "--pdeathsig", "KILL", *argv, *chardevs]
                + ["-object", "monitor-qmp,id=qmp-monitor,chardev=qmp", *extra],
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
            )
        vm = cls(process, log, socket_dir, Qmp(socket_path, lambda: process.poll() is None))
        try:
            try:
                vm._qmp.connect()
            except VmError as e:
                raise VmError(f"QEMU did not start: {e}\n{vm.log_text()}") from None
            # nic1 down from the start: QMP, unlike HMP, reports a wrong
            # device id.
            vm.qmp("set_link", {"name": "nic1", "up": False})
        except BaseException:
            vm.quit()
            raise
        return vm

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.quit()

    @property
    def returncode(self) -> int | None:
        """QEMU's exit status, None while it runs."""
        return self._process.poll()

    def alive(self) -> bool:
        return self.returncode is None

    def qmp(self, command: str, arguments: Mapping[str, object] | None = None) -> object:
        return self._qmp.execute(command, arguments)

    def hmp(self, command_line: str) -> str:
        return self._qmp.hmp(command_line)

    def status(self) -> str | None:
        """The VM's run state (running, paused, shutdown, io-error, ...), None
        if QMP does not answer."""
        try:
            reply = self.qmp("query-status")
        except VmError:
            return None
        return str(reply["status"]) if isinstance(reply, dict) else None

    def check(self) -> None:
        """Fails once QEMU has exited, or has stopped the VM for good: every
        wait loop calls this, so a dead VM ends the wait at once instead of
        at its deadline. Callers that expect the guest's power-off poll
        status() instead."""
        if (rc := self.returncode) is not None:
            raise VmError(f"QEMU has exited with status {rc}:\n{self.log_text()}")
        if (state := self.status()) in _STOPPED:
            raise VmError(f"QEMU has stopped the VM: {state}\n{self.log_text()}")

    def wait_migration(self, timeout: float) -> None:
        """Until a migration (`migrate`, or the restore of -incoming) completes."""
        deadline = time.monotonic() + timeout
        while True:
            if self.returncode is not None:
                raise VmError(f"QEMU exited during the migration:\n{self.log_text()}")
            reply = self.qmp("query-migrate")
            status = str(reply.get("status", "")) if isinstance(reply, dict) else ""
            if status == "completed":
                return
            if status in ("failed", "cancelled"):
                raise VmError(f"migration {status}:\n{self.log_text()}")
            if time.monotonic() >= deadline:
                raise VmError(f"migration still '{status}' after {timeout:g} s")
            time.sleep(0.2)

    def quit(self, timeout: float = 30.0) -> int:
        """Stops QEMU and returns its exit status; kills a QEMU that does not
        quit within timeout. Idempotent."""
        if self._process.poll() is None:
            try:
                self._qmp.quit()
            except VmError:
                self._process.terminate()
            try:
                self._process.wait(timeout)
            except subprocess.TimeoutExpired:
                # A stopped or wedged QEMU acts on neither.
                self._process.kill()
                self._process.wait()
        self._qmp.close()
        shutil.rmtree(self._socket_dir, ignore_errors=True)
        return self._process.returncode

    def log_text(self) -> str:
        return self.log.read_text(errors="replace")
