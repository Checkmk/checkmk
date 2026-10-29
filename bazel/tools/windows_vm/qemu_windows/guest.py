# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import contextlib
import html
import os
import re
import subprocess
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from qemu_windows.errors import VmError
from qemu_windows.qga import Qga, QgaConnectionLost, QgaError, QgaTimeout

USER = "Administrator"
# The test image's fixed Administrator password: the image build writes it
# into Setup's answer file and the autologon, the runners need it for
# schtasks /rp. It is baked into the image, so changing it takes a new image.
# A throwaway VM on a private network. It goes unescaped through the answer
# file's XML, PowerShell and cmd, hence the character set Guest insists on.
PASSWORD = "QemuRunner1!"
_PASSWORD_CHARS = re.compile(r"[A-Za-z0-9!]+")


class GuestError(VmError):
    """A guest command that failed or a guest that did not answer in time."""


# Before every powershell() script: stop at the first error, no progress
# records, and output in UTF-8 rather than the OEM code page.
_PS_PRELUDE = (
    "$ErrorActionPreference = 'Stop'; $ProgressPreference = 'SilentlyContinue'\n"
    "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n"
)
# File transfer chunks. qemu-ga writes each reply to its port in one piece,
# and the guest's virtio-serial driver (vioser) copies a write into one
# non-paged pool buffer, which it must map in at most 128 runs of physical
# memory: a larger reply is lost without an error to the host, from 512 KiB
# up when that pool is fragmented (a read's data is base64, a third
# larger). Reads stay well below. Larger writes are no faster.
_READ_CHUNK = 256 * 1024
_WRITE_CHUNK = 1024 * 1024
# One wait_ready attempt. While the guest boots, QEMU takes the connection
# but nothing answers: a short attempt notices the agent soon after it starts.
_PING_TIMEOUT = 5.0


@dataclass(frozen=True)
class Guest:
    """The guest, through its agent (qemu-ga, Qga).

    qemu-ga runs as LocalSystem in session 0: what needs the Administrator
    or the console session goes through session.run_in_session. Commands
    are argument lists, never shell strings. check() raises once the VM is
    gone (Qemu.check), so a wait fails at once instead of at its deadline.
    Paths in the guest are Windows paths.
    """

    agent: Qga
    check: Callable[[], None]
    user: str = USER
    password: str = PASSWORD

    def __post_init__(self) -> None:
        if not _PASSWORD_CHARS.fullmatch(self.password):
            raise GuestError("the guest password may only contain letters, digits and '!'")

    def run(
        self, argv: Sequence[str], *, check: bool = True, timeout: float = 3600.0
    ) -> subprocess.CompletedProcess[str]:
        """Runs argv[0] (found on the guest's PATH) with the arguments
        argv[1:]; its output with Windows' CRs removed.

        The agent hands the output over in one reply once the program has
        exited, and a reply larger than 512 KiB can be lost (_READ_CHUNK): a
        program with more output writes it to a file, for read() or get().
        """
        command = subprocess.list2cmdline(argv)
        try:
            started = self._record(
                "guest-exec", {"path": argv[0], "arg": list(argv[1:]), "capture-output": True}
            )
        except GuestError as e:
            raise GuestError(f"'{command}' did not start: {e}") from None
        deadline = time.monotonic() + timeout
        interval = 0.05
        while not (status := self._status(command, started["pid"]))["exited"]:
            self.check()
            if time.monotonic() >= deadline:
                raise GuestError(f"'{command}' did not finish within {timeout:g} s")
            time.sleep(interval)
            interval = min(2 * interval, 1.0)
        stdout, stderr = (
            base64.b64decode(str(status.get(f"{stream}-data", "")))
            .decode(errors="replace")
            .replace("\r", "")
            for stream in ("out", "err")
        )
        # An NTSTATUS (0xC...) for a program that crashed.
        crashed = "signal" in status
        returncode = int(str(status["signal" if crashed else "exitcode"]))
        result = subprocess.CompletedProcess(argv, returncode, stdout, stderr)
        if check and returncode != 0:
            how = (
                f"crashed ({returncode & 0xFFFFFFFF:#010x})"
                if crashed
                else f"failed (exit {returncode})"
            )
            raise GuestError(f"'{command}' {how} in the guest:\n{stdout}{stderr}")
        return result

    def powershell(
        self, script: str, *, check: bool = True, timeout: float = 3600.0
    ) -> subprocess.CompletedProcess[str]:
        """Runs a Windows PowerShell script, which stops at its first error
        (exit 1). It goes as -EncodedCommand (UTF-16LE, base64), which no
        quoting rule can mangle."""
        encoded = base64.b64encode((_PS_PRELUDE + script).encode("utf-16-le")).decode()
        result = self.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            check=False,
            timeout=timeout,
        )
        result.stderr = _from_clixml(result.stderr)
        if check and result.returncode != 0:
            raise GuestError(
                f"PowerShell script failed in the guest (exit {result.returncode}):\n{script}\n"
                + result.stdout
                + result.stderr
            )
        return result

    def exists(self, path: str) -> bool:
        """Whether a file or directory exists in the guest."""
        return self.powershell(f"Test-Path -LiteralPath {ps_quote(path)}").stdout.strip() == "True"

    def put(self, local: Path, remote: str) -> None:
        """Copies the file local into the guest, as remote."""
        with local.open("rb") as source:
            self._write(remote, iter(lambda: source.read(_WRITE_CHUNK), b""))

    def get(self, remote: str, local: Path) -> None:
        """Copies the guest's file remote out of the guest, as local, which
        a failed copy leaves as it was: the copy goes to a file next to it
        first."""
        partial = local.with_name(f".{local.name}.{os.getpid()}.part")
        try:
            with partial.open("wb") as target:
                for chunk in self._read(remote):
                    target.write(chunk)
            partial.replace(local)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise

    def read(self, remote: str) -> bytes:
        """The content of the guest's file remote."""
        return b"".join(self._read(remote))

    def write(self, remote: str, data: bytes) -> None:
        """Creates or replaces the guest's file remote with data."""
        self._write(remote, (data[i : i + _WRITE_CHUNK] for i in range(0, len(data), _WRITE_CHUNK)))

    def wait_ready(self, timeout: float, interval: float = 1.0) -> None:
        """Until the guest agent answers. On failure, shows why the last
        attempt failed."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.agent.execute("guest-ping", timeout=_PING_TIMEOUT)
                return
            except QgaError as e:
                error = e
            self.check()
            if time.monotonic() >= deadline:
                raise GuestError(f"no guest agent within {timeout:g} s: {error}")
            time.sleep(interval)

    def wait_console(self, timeout: float) -> None:
        """Until the autologon console session is active. `query user` exits
        1 even when it lists sessions, so only its output counts."""
        deadline = time.monotonic() + timeout
        while not any(
            "console" in line and "active" in line
            for line in self.run(["query.exe", "user"], check=False).stdout.lower().splitlines()
        ):
            self.check()
            if time.monotonic() >= deadline:
                raise GuestError(f"no autologon console session within {timeout:g} s")
            time.sleep(1)

    def set_clock(self) -> None:
        """The guest clock from the host's: a saved state resumes with the
        time it was saved at, and w32time does not correct steps of days
        (nor can it reach an NTP server without internet)."""
        self._agent("guest-set-time", {"time": time.time_ns()})

    def shutdown(self) -> None:
        """Asks the guest to power off: the caller waits for QEMU to report
        it. The agent answers only if it cannot, and then at once."""
        try:
            self.agent.execute("guest-shutdown", {"mode": "powerdown"}, timeout=2)
        except QgaTimeout, QgaConnectionLost:
            pass
        except QgaError as e:
            raise GuestError(str(e)) from None

    def _status(self, command: str, pid: object) -> dict[str, object]:
        try:
            return self._record("guest-exec-status", {"pid": pid})
        except GuestError as e:
            raise GuestError(
                f"'{command}': {e} (its reply is also lost when the program's output"
                " makes it larger than 512 KiB)"
            ) from None

    def _agent(self, command: str, arguments: dict[str, object]) -> object:
        try:
            return self.agent.execute(command, arguments)
        except QgaError as e:
            raise GuestError(str(e)) from None

    def _record(self, command: str, arguments: dict[str, object]) -> dict[str, object]:
        if not isinstance(reply := self._agent(command, arguments), dict):
            raise GuestError(f"{command}: unexpected reply {reply!r}")
        return reply

    def _read(self, remote: str) -> Iterator[bytes]:
        handle = self._agent("guest-file-open", {"path": remote, "mode": "rb"})
        try:
            while True:
                reply = self._record("guest-file-read", {"handle": handle, "count": _READ_CHUNK})
                yield base64.b64decode(str(reply["buf-b64"]))
                if reply["eof"] or not reply["count"]:
                    break
        finally:
            self._close(handle)

    def _write(self, remote: str, chunks: Iterable[bytes]) -> None:
        handle = self._agent("guest-file-open", {"path": remote, "mode": "wb"})
        try:
            for chunk in chunks:
                reply = self._record(
                    "guest-file-write",
                    {"handle": handle, "buf-b64": base64.b64encode(chunk).decode()},
                )
                if reply["count"] != len(chunk):
                    raise GuestError(f"{remote}: {reply['count']} of {len(chunk)} bytes written")
        except BaseException:
            self._close(handle)
            raise
        # Its error matters here: the last writes may only land with it.
        self._agent("guest-file-close", {"handle": handle})

    def _close(self, handle: object) -> None:
        # An open handle locks the file for as long as qemu-ga runs.
        with contextlib.suppress(GuestError):
            self._agent("guest-file-close", {"handle": handle})


def _from_clixml(stderr: str) -> str:
    """PowerShell's error output as text: given -EncodedCommand, it writes
    it as CLIXML."""
    if not stderr.startswith("#< CLIXML"):
        return stderr
    return "".join(
        re.sub(r"_x([0-9A-Fa-f]{4})_", lambda c: chr(int(c[1], 16)), html.unescape(record))
        for record in re.findall(r'<S S="\w+">(.*?)</S>', stderr, re.DOTALL)
    ).replace("\r", "")


def ps_quote(text: str) -> str:
    """text as a PowerShell string literal, for powershell() scripts."""
    return "'" + text.replace("'", "''") + "'"
