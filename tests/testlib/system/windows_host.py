#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""A Windows machine that a system test drives over SSH, with the OpenSSH client of the test
container.

The machine runs Windows OpenSSH, whose default shell is Windows PowerShell 5.1. That shell
silently drops everything after the first line of a command it reads from stdin, so WindowsHost
passes every command as an argument of ssh.

Windows OpenSSH does not end the processes of a session whose connection drops. A command that
runs into its timeout here keeps running on the machine.
"""

import logging
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath

from tests.testlib.common.utils import wait_until

logger = logging.getLogger(__name__)

_TIMEOUT = 300


def quote(argument: str) -> str:
    """Quote argument as a literal string for PowerShell. For example, it's becomes 'it''s'.

    Windows PowerShell 5.1 corrupts three kinds of argument on their way to a native command such
    as powershell.exe: it strips double quotes, it drops an empty string, and it wraps an argument
    with whitespace in double quotes, so that a trailing backslash escapes the closing quote.
    """
    if (
        '"' in argument
        or argument == ""
        or (any(c.isspace() for c in argument) and argument.endswith("\\"))
    ):
        raise ValueError(f"Windows PowerShell 5.1 cannot pass {argument!r} to a script")
    return "'" + argument.replace("'", "''") + "'"


class WindowsHost:
    """One SSH connection to a Windows machine, shared by all commands and copies.

    Get an instance from connect(). The connection is an OpenSSH master connection, which also
    carries the remote forwards of forward_to_local_port().
    """

    def __init__(self, hostname: str, base_options: Sequence[str]) -> None:
        self.hostname = hostname
        self._base_options = list(base_options)

    def run(
        self, command: str, *, check: bool = True, timeout: float = _TIMEOUT
    ) -> subprocess.CompletedProcess[str]:
        """Run PowerShell commands, as the account of the connection."""
        return _run(
            ["ssh", *self._base_options, self.hostname, command], check=check, timeout=timeout
        )

    def run_script(
        self, script: PureWindowsPath, *args: str, check: bool = True, timeout: float = _TIMEOUT
    ) -> subprocess.CompletedProcess[str]:
        """Run a PowerShell script that lies on the machine, and pass its exit code on."""
        return self.run(_script_command(script, args), check=check, timeout=timeout)

    def start_script(self, script: PureWindowsPath, *args: str) -> subprocess.Popen[str]:
        """Start a PowerShell script on a connection of its own, and return without waiting.

        Ending the returned process drops that connection. The script itself keeps running,
        unless it watches its session.
        """
        return subprocess.Popen(
            [
                "ssh",
                # ssh takes the first value of an option, so this one wins over the master's.
                *("-o", "ControlPath=none"),
                *self._base_options,
                self.hostname,
                _script_command(script, args),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def copy_to(self, source: Path, target: PureWindowsPath) -> None:
        self._scp(source.as_posix(), f"{self.hostname}:{target.as_posix()}")

    def copy_from(self, source: PureWindowsPath, target: Path) -> None:
        self._scp(f"{self.hostname}:{source.as_posix()}", target.as_posix())

    def forward_to_local_port(self, local_port: int) -> int:
        """Let the machine reach local_port of this side on 127.0.0.1:<returned port>.

        The machine picks a free port. The forward lasts as long as the connection.
        """
        forward = self._ssh_control("forward", "-R", f"0:127.0.0.1:{local_port}")
        return int(forward.stdout.strip())

    def _ssh_control(self, *args: str) -> subprocess.CompletedProcess[str]:
        return _control(self._base_options, self.hostname, *args)

    def _scp(self, source: str, target: str) -> None:
        _run(["scp", "-q", *self._base_options, source, target], check=True, timeout=_TIMEOUT)


@contextmanager
def connect(hostname: str, user: str, key_file: Path) -> Iterator[WindowsHost]:
    """Open the master connection to hostname, and close it with every remote forward on exit.

    The host key is accepted on first contact and forgotten afterwards. The machine is a test
    host that its owners redeploy, and a redeploy changes its host key.

    connect() takes no lock. Runs share the host win-agenttest-ci.lan.checkmk.net, so tests reach
    it only through the fixtures in non-free/tests/system/agent_updates/windows/conftest.py, which
    hold the lock of the host.
    """
    with tempfile.TemporaryDirectory(prefix="winssh-") as tmp:
        # A Unix socket path must stay below 108 bytes, so the control socket lives in a short
        # temporary directory rather than in a pytest tmp_path.
        control_path = Path(tmp, "control")
        base_options = [
            *("-o", "BatchMode=yes"),
            *("-o", "IdentitiesOnly=yes"),
            *("-i", key_file.as_posix()),
            *("-o", f"User={user}"),
            *("-o", "StrictHostKeyChecking=accept-new"),
            *("-o", f"UserKnownHostsFile={Path(tmp, 'known_hosts').as_posix()}"),
            *("-o", "ConnectTimeout=10"),
            *("-o", "ServerAliveInterval=15"),
            *("-o", f"ControlPath={control_path.as_posix()}"),
        ]
        # The master reports every refused connection of a remote forward on stderr. A pipe
        # that nobody reads would fill up and block the master.
        master_log = Path(tmp, "master.log")
        with master_log.open("w") as log:
            master = subprocess.Popen(
                ["ssh", *base_options, *("-o", "ControlMaster=yes"), "-N", hostname],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=log,
            )
        try:
            try:
                wait_until(
                    lambda: control_path.exists() or master.poll() is not None,
                    timeout=30,
                    interval=0.2,
                    condition_name=f"the SSH connection to {hostname}",
                )
            except TimeoutError:
                raise RuntimeError(
                    f"SSH to {user}@{hostname} did not connect:\n{master_log.read_text()}"
                ) from None
            if master.poll() is not None:
                raise RuntimeError(
                    f"SSH to {user}@{hostname} failed with exit code {master.returncode}:\n"
                    f"{master_log.read_text()}"
                )
            yield WindowsHost(hostname, base_options)
        finally:
            if master.poll() is None:
                try:
                    _control(base_options, hostname, "exit", check=False)
                except subprocess.TimeoutExpired:
                    logger.warning("ssh -O exit to %s timed out", hostname)
                try:
                    master.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    master.kill()
                    master.wait()


def _script_command(script: PureWindowsPath, args: Sequence[str]) -> str:
    return " ".join(
        [
            "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File",
            quote(str(script)),
            *(quote(arg) for arg in args),
            "; exit $LASTEXITCODE",
        ]
    )


def _control(
    base_options: Sequence[str], hostname: str, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return _run(["ssh", *base_options, "-O", *args, hostname], check=check, timeout=30)


def _run(args: Sequence[str], *, check: bool, timeout: float) -> subprocess.CompletedProcess[str]:
    logger.debug("Running %s", args)
    # Windows PowerShell 5.1 writes in the OEM code page of the machine. Characters outside
    # ASCII arrive garbled instead of breaking the decoding.
    completed = subprocess.run(
        args,
        # Without this, ssh would pass the terminal of pytest on to the remote shell.
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"{args[0]} failed with exit code {completed.returncode}: {args}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed
